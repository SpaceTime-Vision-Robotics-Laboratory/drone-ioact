from robobase import ActionsQueue, DataChannel, Action as A
from roboimpl.controllers import ScreenDisplayer

def test_ScreenDisplayer_keyboard_mock_queue():
    key_to_action = {"Q": A("act_Q"), "X": A("act_X"), "Key.esc": A("act_esc")}
    aq = ActionsQueue(action_names=[a.name for a in key_to_action.values()])
    data_channel = DataChannel(supported_types=["dummy"], eq_fn=lambda a, b: True)
    sd = ScreenDisplayer(data_channel=data_channel, actions_queue=aq, key_to_action=key_to_action, backend="tkinter")

    def make_keypress(keysym: str):
        sd._on_event(keysym)

    make_keypress("a")
    assert len(aq) == 0
    make_keypress("Q")
    assert len(aq) == 1
    make_keypress("X")
    assert len(aq) == 2
    assert aq.get()[0].name == "act_Q"
    assert len(aq) == 1
    make_keypress("Key.esc")
    assert len(aq) == 2
    make_keypress("Key.QQ")
    assert len(aq) == 2
    assert aq.get()[0].name == "act_X"
    assert aq.get()[0].name == "act_esc"
    assert len(aq) == 0

def test_ScreenDisplayer_key_to_actions():
    aq = ActionsQueue(action_names=["act1", "act2"])
    data_channel = DataChannel(supported_types=["dummy"], eq_fn=lambda a, b: True)
    key_to_action = {"A": A("act1", (5, )), "B": A("act2")}
    sd = ScreenDisplayer(data_channel=data_channel, actions_queue=aq, key_to_action=key_to_action)
    assert {a.name for a in sd.key_to_action.values()} == {"act1", "act2"}
