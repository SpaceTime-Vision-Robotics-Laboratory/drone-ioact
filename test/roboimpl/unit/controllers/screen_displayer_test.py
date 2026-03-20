from robobase import ActionsQueue, DataChannel, Action as A
from roboimpl.controllers import ScreenDisplayer, Key
import pytest

def test_ScreenDisplayer_keyboard_mock_queue():
    key_to_action = {Key.q: A("act_Q"), Key.x: A("act_X"), Key.Esc: A("act_esc")}
    aq = ActionsQueue(action_names=[a.name for a in key_to_action.values()])
    data_channel = DataChannel(supported_types=["dummy"], eq_fn=lambda a, b: True)
    sd = ScreenDisplayer(data_channel=data_channel, actions_queue=aq, key_to_action=key_to_action, backend="tkinter")

    def make_keypress(key: Key):
        sd._on_event(key)

    make_keypress(Key.a)
    assert len(aq) == 0
    make_keypress(Key.q)
    assert len(aq) == 1
    make_keypress(Key.x)
    assert len(aq) == 2
    assert aq.get()[0].name == "act_Q"
    assert len(aq) == 1
    make_keypress(Key.Esc)
    assert len(aq) == 2
    with pytest.raises(AttributeError):
        make_keypress(Key.QQ)
    assert len(aq) == 2
    assert aq.get()[0].name == "act_X"
    assert aq.get()[0].name == "act_esc"
    assert len(aq) == 0

def test_ScreenDisplayer_key_to_actions():
    aq = ActionsQueue(action_names=["act1", "act2"])
    data_channel = DataChannel(supported_types=["dummy"], eq_fn=lambda a, b: True)
    key_to_action = {Key.a: A("act1", (5, )), Key.b: A("act2")}
    sd = ScreenDisplayer(data_channel=data_channel, actions_queue=aq, key_to_action=key_to_action)
    assert {a.name for a in sd.key_to_action.values()} == {"act1", "act2"}
