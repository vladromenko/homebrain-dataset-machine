"""Transcript gating tests do not establish acoustic false-activation rates."""
from homebrain.audio import wake_command


def test_wake_phrase_requires_explicit_prefix():
    assert wake_command("Hey, Homebrain, help me collect the dataset.")=="help me collect the dataset."
    assert wake_command("hey home brain repeat the instruction")=="repeat the instruction"
    assert wake_command("Homebrain is ready.") is None
    assert wake_command("Someone said hey Homebrain help") is None
    assert wake_command("Check the calibration") is None
    assert wake_command("") is None
