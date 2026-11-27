"""Transcript gating tests do not establish acoustic false-activation rates."""
from homebrain.audio import wake_command


def test_wake_phrase_requires_explicit_prefix():
    assert wake_command("Hey, Homebrain, help me collect the dataset.")=="help me collect the dataset."
    assert wake_command("hey home brain repeat the instruction")=="repeat the instruction"
    assert wake_command("Homebrain is ready.") is None
    assert wake_command("Someone said hey Homebrain help") is None
    assert wake_command("Check the calibration") is None
    assert wake_command("") is None


def test_capture_timeout_releases_only_its_own_process(tmp_path,monkeypatch):
    import subprocess
    from types import SimpleNamespace
    from unittest.mock import Mock
    import pytest
    from homebrain.audio import Audio
    process = Mock()
    process.poll.return_value = None
    process.communicate.side_effect = [subprocess.TimeoutExpired('arecord',4),(b'',b'')]
    monkeypatch.setattr(subprocess,'Popen',Mock(return_value=process))
    microphone = SimpleNamespace(state='Ready',authorized='usb-id',
        selected={'id':'usb-id','alsa':'persistent-pcm'},refresh=Mock())
    audio = Audio(tmp_path)
    with pytest.raises(subprocess.TimeoutExpired):
        audio.capture(microphone,1)
    process.terminate.assert_called_once_with()
    process.kill.assert_not_called()
    assert audio.recording is None and microphone.state=='Recovering'
