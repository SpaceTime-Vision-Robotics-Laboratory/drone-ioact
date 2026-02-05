from pytest_mock import MockerFixture
from queue import Queue
from robobase import ActionsQueue, DataChannel
from roboimpl.controllers import ScreenDisplayer

def test_KeyboardController_mock_queue(mocker: MockerFixture):
    key_to_action = {"Q": "act_Q", "X": "act_X", "Key.esc": "act_esc"}
    actions_queue = ActionsQueue(actions=list(key_to_action.values()), queue=(q := Queue()))
    data_channel = DataChannel(supported_types=["dummy"], eq_fn=lambda a, b: True)
    sd = ScreenDisplayer(data_channel=data_channel, actions_queue=actions_queue, key_to_action=key_to_action)

    def make_keypress(keysym: str):
        mock_event = mocker.Mock()
        mock_event.keysym = keysym
        sd._on_key_release(mock_event)

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
