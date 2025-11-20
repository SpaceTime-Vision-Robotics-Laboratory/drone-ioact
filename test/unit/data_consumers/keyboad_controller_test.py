from pytest_mock import MockerFixture
from drone_ioact.data_consumers import KeyboardController
from drone_ioact import ActionsQueue, DataChannel
from queue import Queue

def test_KeyboardController_mock_queue(mocker: MockerFixture):
    key_to_action = {"Q": "act_Q", "X": "act_X", "Key.esc": "act_esc"}
    actions_queue = ActionsQueue(q := Queue(), actions=list(key_to_action.values()))
    data_channel = DataChannel(supported_types=["dummy"], eq_fn=lambda a, b: True)
    kbc = KeyboardController(data_channel=data_channel, actions_queue=actions_queue, key_to_action=key_to_action)
    mocker.patch.object(kbc, "listener", mocker.Mock()) # Use mocker to fake the listener, so no real keyboard hooks

    def make_keypress(char: str):
        key = mocker.MagicMock()
        key.char = char
        key.__str__.return_value = char
        kbc.on_release(key)

    make_keypress("a")
    assert len(q.queue) == 0
    make_keypress("Q")
    assert len(q.queue) == 1
    make_keypress("X")
    assert len(q.queue) == 2
    assert q.get() == "act_Q"
    assert len(q.queue) == 1
    make_keypress("Key.esc")
    assert len(q.queue) == 2
    make_keypress("Key.QQ")
    assert len(q.queue) == 2
    assert q.get() == "act_X"
    assert q.get() == "act_esc"
    assert len(q.queue) == 0
