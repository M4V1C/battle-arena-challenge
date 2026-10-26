
from avatar_repository import RepositorioAvatares


def test_avatares_iniciales(tmp_path):
    repositorio = RepositorioAvatares(tmp_path / "avatars.json")

    assert repositorio.obtener() == {
        "red": "avatar_1",
        "blue": "avatar_2",
    }


def test_guardar_avatar(tmp_path):
    repositorio = RepositorioAvatares(tmp_path / "avatars.json")

    repositorio.guardar("red", "avatar_3")

    assert repositorio.obtener()["red"] == "avatar_3"
    assert repositorio.obtener()["blue"] == "avatar_2"


def test_persistencia(tmp_path):
    ruta = tmp_path / "avatars.json"

    primer_repositorio = RepositorioAvatares(ruta)
    primer_repositorio.guardar("blue", "avatar_5")

    segundo_repositorio = RepositorioAvatares(ruta)

    assert segundo_repositorio.obtener()["blue"] == "avatar_5"
