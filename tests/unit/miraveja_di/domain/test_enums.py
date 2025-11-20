"""Unit tests for domain enums."""

import pytest

from miraveja_di.domain.enums import Lifetime


class TestLifetimeEnum:
    """Test cases for the Lifetime enum."""

    def test_singleton_value(self):
        """Test that SINGLETON has correct string value."""
        assert Lifetime.SINGLETON.value == "singleton"

    def test_transient_value(self):
        """Test that TRANSIENT has correct string value."""
        assert Lifetime.TRANSIENT.value == "transient"

    def test_scoped_value(self):
        """Test that SCOPED has correct string value."""
        assert Lifetime.SCOPED.value == "scoped"

    def test_lifetime_comparison(self):
        """Test that lifetime enums can be compared for equality."""
        assert Lifetime.SINGLETON == Lifetime.SINGLETON
        assert Lifetime.TRANSIENT != Lifetime.SINGLETON
        assert Lifetime.SCOPED != Lifetime.TRANSIENT

    def test_lifetime_from_value(self):
        """Test that lifetime can be created from string value."""
        assert Lifetime("singleton") == Lifetime.SINGLETON
        assert Lifetime("transient") == Lifetime.TRANSIENT
        assert Lifetime("scoped") == Lifetime.SCOPED

    def test_invalid_lifetime_value_raises_error(self):
        """Test that invalid lifetime value raises ValueError."""
        with pytest.raises(ValueError, match="'invalid' is not a valid Lifetime"):
            Lifetime("invalid")

    def test_lifetime_enum_members(self):
        """Test that all expected enum members exist."""
        expected_members = {"SINGLETON", "TRANSIENT", "SCOPED"}
        actual_members = {member.name for member in Lifetime}
        assert actual_members == expected_members

    def test_lifetime_enum_count(self):
        """Test that enum has exactly three members."""
        assert len(list(Lifetime)) == 3

    def test_lifetime_string_representation(self):
        """Test string representation of lifetime enums."""
        assert str(Lifetime.SINGLETON) == "singleton"
        assert str(Lifetime.TRANSIENT) == "transient"
        assert str(Lifetime.SCOPED) == "scoped"

    def test_lifetime_repr_representation(self):
        """Test repr representation of lifetime enums."""
        assert repr(Lifetime.SINGLETON) == "<Lifetime.SINGLETON: 'singleton'>"
        assert repr(Lifetime.TRANSIENT) == "<Lifetime.TRANSIENT: 'transient'>"
        assert repr(Lifetime.SCOPED) == "<Lifetime.SCOPED: 'scoped'>"

    def test_lifetime_iteration(self):
        """Test that lifetime enum can be iterated."""
        lifetimes = list(Lifetime)
        assert Lifetime.SINGLETON in lifetimes
        assert Lifetime.TRANSIENT in lifetimes
        assert Lifetime.SCOPED in lifetimes

    def test_lifetime_membership(self):
        """Test that membership check works for lifetime values."""
        assert "singleton" in [member.value for member in Lifetime]
        assert "transient" in [member.value for member in Lifetime]
        assert "scoped" in [member.value for member in Lifetime]
        assert "invalid" not in [member.value for member in Lifetime]

    def test_lifetime_hashable(self):
        """Test that lifetime enums are hashable and can be used in sets."""
        lifetime_set = {Lifetime.SINGLETON, Lifetime.TRANSIENT, Lifetime.SCOPED}
        assert len(lifetime_set) == 3
        assert Lifetime.SINGLETON in lifetime_set

    def test_lifetime_can_be_used_as_dict_key(self):
        """Test that lifetime enums can be used as dictionary keys."""
        lifetime_dict = {Lifetime.SINGLETON: "single", Lifetime.TRANSIENT: "new", Lifetime.SCOPED: "scoped"}
        assert lifetime_dict[Lifetime.SINGLETON] == "single"
        assert lifetime_dict[Lifetime.TRANSIENT] == "new"
        assert lifetime_dict[Lifetime.SCOPED] == "scoped"
