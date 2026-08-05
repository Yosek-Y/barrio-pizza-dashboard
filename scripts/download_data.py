"""Descarga los cuatro CSV oficiales del reto técnico."""

from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

BASE_URL = (
    "https://raw.githubusercontent.com/soydelbarrio/"
    "reto-practicante-ia/master/datos"
)
FILES = (
    "ingredientes.csv",
    "consumo_historico.csv",
    "inventario_actual.csv",
    "orden_compra_semana.csv",
)
DESTINATION = Path(__file__).resolve().parents[1] / "datos"


def download_file(filename: str) -> None:
    """Descarga un archivo y lo guarda sin modificar sus bytes."""
    url = f"{BASE_URL}/{filename}"
    destination = DESTINATION / filename

    try:
        with urlopen(url, timeout=30) as response:  # noqa: S310 - URL fija y controlada
            content = response.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"No se pudo descargar {filename}: {exc}") from exc

    destination.write_bytes(content)
    print(f"Descargado: {destination}")


def main() -> None:
    """Descarga todos los archivos requeridos."""
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for filename in FILES:
        download_file(filename)


if __name__ == "__main__":
    main()
