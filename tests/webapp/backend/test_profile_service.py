#!/usr/bin/env python3
"""Tests for the profile lifecycle service (create/duplicate/register/delete)."""

from pathlib import Path

import pytest

from jobjob.loader.profiles import Profile
from services import profile_service as PS


def _profile(name: str, path: Path, *, read_only: bool = False, owned: bool = False):
    return Profile(name=name, path=Path(path), read_only=read_only, owned=owned)


@pytest.fixture
def home(tmp_path):
    """A scaffolded home: <home>/config/.env, returns (home, app_config_path)."""
    cfg = tmp_path / "config" / ".env"
    cfg.parent.mkdir(parents=True)
    cfg.write_text('CLAUDE_MODEL="m"\n')
    return tmp_path, cfg


def _registry_value(cfg: Path, name: str) -> str | None:
    key = PS.registry_key(name)
    for line in cfg.read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip().strip('"')
    return None


class TestNormalize:
    def test_lowercases_and_validates(self):
        assert PS.normalize_name("  My_Prof ") == "my_prof"

    @pytest.mark.parametrize(
        "bad", ["", "example", "active", "1abc", "has-hyphen", "a b"]
    )
    def test_rejects(self, bad):
        with pytest.raises(PS.ProfileError):
            PS.normalize_name(bad)


class TestCreate:
    def test_creates_and_registers_blank(self, home):
        _, cfg = home
        dest = PS.create_profile(cfg, {"example": Path("/x")}, "alpha")
        assert (dest / "content" / "highlights.toml").is_file()
        assert (dest / "config" / ".profile").is_file()
        assert dest == PS.profiles_base(cfg) / "alpha"
        assert _registry_value(cfg, "alpha") == str(dest)

    def test_rejects_duplicate_name(self, home):
        _, cfg = home
        with pytest.raises(PS.ProfileError):
            PS.create_profile(cfg, {"alpha": Path("/x")}, "alpha")


class TestDuplicate:
    def test_copies_source_tree(self, home, tmp_path):
        _, cfg = home
        src = tmp_path / "src"
        PS.create_profile(cfg, {}, "alpha")  # make a valid source under home
        src = PS.profiles_base(cfg) / "alpha"
        dest = PS.duplicate_profile(cfg, {"alpha": src}, "alpha", "beta")
        assert (dest / "content" / "highlights.toml").is_file()
        assert _registry_value(cfg, "beta") == str(dest)

    def test_unknown_source(self, home):
        _, cfg = home
        with pytest.raises(PS.ProfileError):
            PS.duplicate_profile(cfg, {}, "ghost", "beta")


class TestRegister:
    def test_registers_existing_valid_dir(self, home, tmp_path):
        _, cfg = home
        ext = tmp_path / "external"
        from jobjob.loader.skeleton import create_blank_profile

        create_blank_profile(ext)
        loc = PS.register_profile(cfg, {}, "ext", str(ext))
        assert loc == ext.resolve()
        assert _registry_value(cfg, "ext") == str(ext.resolve())

    def test_rejects_invalid_dir(self, home, tmp_path):
        _, cfg = home
        bad = tmp_path / "bad"
        bad.mkdir()
        with pytest.raises(PS.ProfileError):
            PS.register_profile(cfg, {}, "bad", str(bad))


class TestValidate:
    def test_requires_profile_config_and_content(self, tmp_path):
        d = tmp_path / "p"
        (d / "content").mkdir(parents=True)
        with pytest.raises(PS.ProfileError):
            PS.validate_profile_dir(d)  # no config/.profile

    def test_rejects_bad_toml(self, tmp_path):
        from jobjob.loader.skeleton import create_blank_profile

        d = create_blank_profile(tmp_path / "p")
        (d / "content" / "skills.toml").write_text("not = [valid")
        with pytest.raises(PS.ProfileError):
            PS.validate_profile_dir(d)


class TestDelete:
    def test_unregisters_and_removes_owned_dir(self, home):
        _, cfg = home
        dest = PS.create_profile(cfg, {}, "alpha")
        removed = PS.delete_profile(
            cfg, _profile("alpha", dest, owned=True), active_name="local"
        )
        assert removed is True
        assert not dest.exists()
        assert _registry_value(cfg, "alpha") is None

    def test_keeps_external_files(self, home, tmp_path):
        _, cfg = home
        from jobjob.loader.skeleton import create_blank_profile

        ext = create_blank_profile(tmp_path / "external")
        PS.register_profile(cfg, {}, "ext", str(ext))
        removed = PS.delete_profile(
            cfg, _profile("ext", ext.resolve(), owned=False), active_name="local"
        )
        assert removed is False
        assert ext.exists()  # never delete files we did not create
        assert _registry_value(cfg, "ext") is None

    def test_refuses_active(self, home):
        _, cfg = home
        dest = PS.create_profile(cfg, {}, "alpha")
        with pytest.raises(PS.ProfileError):
            PS.delete_profile(
                cfg, _profile("alpha", dest, owned=True), active_name="alpha"
            )

    def test_refuses_read_only_example(self, home):
        _, cfg = home
        from jobjob.loader.profiles import bundled_example_dir

        with pytest.raises(PS.ProfileError):
            PS.delete_profile(
                cfg,
                _profile("example", bundled_example_dir(), read_only=True),
                active_name="local",
            )


# __END__
