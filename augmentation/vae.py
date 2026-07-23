import torch
import torch.nn as nn
import torch.nn.functional as F


class FeatureVAE(nn.Module):
    """
    Lightweight variational autoencoder over flat engineered feature vectors
    (NOT raw signals or sequences -- one window's feature vector at a time).
    Used for two purposes in Spandana:
      1. Trained on HEALTHY-only vectors, its reconstruction error becomes
         `anomaly_score` at inference (inference/predict.py) -- an
         unsupervised "how far from normal operation is this reading"
         signal, independent of the supervised classifier.
      2. Trained on a minority class's real vectors, it can generate
         additional synthetic samples of that class to rebalance training
         data -- see augmentation/augment_training_data.py, which only
         keeps this if it measurably improves validation macro-F1.
    """

    def __init__(self, input_dim: int, latent_dim: int = 8, hidden_dim: int = 32):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim), nn.ReLU(),
        )
        self.fc_mu = nn.Linear(hidden_dim, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim, latent_dim)

        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, input_dim),
        )
        self.latent_dim = latent_dim

    def encode(self, x):
        h = self.encoder(x)
        return self.fc_mu(h), self.fc_logvar(h)

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def decode(self, z):
        return self.decoder(z)

    def forward(self, x):
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar) if self.training else mu
        recon = self.decode(z)
        return recon, mu, logvar

    def loss(self, x, recon, mu, logvar, kl_weight: float = 0.01):
        recon_loss = F.mse_loss(recon, x, reduction="mean")
        kl_loss = -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp())
        return recon_loss + kl_weight * kl_loss, recon_loss, kl_loss

    @torch.no_grad()
    def reconstruction_error(self, x: torch.Tensor, dims_mask: list = None) -> torch.Tensor:
        """
        Per-sample MSE reconstruction error -- used as anomaly_score.
        `dims_mask` restricts the error to a subset of feature dimensions:
        this project's canonical 24-dim schema has several fields that are
        always zero-filled for a given data source/modality (e.g. a bearing
        vibration reading never populates temperature/current/rpm/hotspot
        fields). Those dims reconstruct trivially for ANY sample from that
        source regardless of its actual health, which dilutes the error
        signal if included -- pass the indices of the dims this source
        actually populates to get a meaningful anomaly score instead.
        """
        self.eval()
        recon, _mu, _logvar = self.forward(x)
        sq_err = (recon - x) ** 2
        if dims_mask is not None:
            sq_err = sq_err[:, dims_mask]
        return sq_err.mean(dim=1)

    @torch.no_grad()
    def generate(self, n: int, device: torch.device) -> torch.Tensor:
        """Samples n synthetic feature vectors from the learned latent prior."""
        self.eval()
        z = torch.randn(n, self.latent_dim, device=device)
        return self.decode(z)


def train_vae(X: torch.Tensor, input_dim: int, epochs: int = 100, batch_size: int = 128,
              lr: float = 1e-3, latent_dim: int = 8, hidden_dim: int = 32,
              device: torch.device = torch.device("cpu")) -> FeatureVAE:
    model = FeatureVAE(input_dim=input_dim, latent_dim=latent_dim, hidden_dim=hidden_dim).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    dataset = torch.utils.data.TensorDataset(X)
    loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)

    model.train()
    for _epoch in range(epochs):
        for (xb,) in loader:
            xb = xb.to(device)
            optimizer.zero_grad()
            recon, mu, logvar = model(xb)
            loss, _r, _k = model.loss(xb, recon, mu, logvar)
            loss.backward()
            optimizer.step()
    return model
