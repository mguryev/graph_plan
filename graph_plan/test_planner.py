import pytest

from .planner import Planner, Action, Layer


def build_layer(**kwargs):
    empty_layer = Layer(
        actions=[],
        propositions=set(),
        mutex_actions={},
        mutex_propositions={},
    )

    return empty_layer.copy(
        **kwargs
    )


def test_build_layer_empty():
    planner = Planner()

    next_layer = planner.calculate_next_layer(
        current_state=build_layer(),
        available_actions=[],
    )

    assert next_layer == Layer(
        actions=[],
        propositions=set(),
    )


def test_next_actions():
    planner = Planner()

    action_add_x = Action(
        name='add_x',
        requirements={},
        add_effects={},
        delete_effects={},
    )

    possible_actions = planner._calculate_actions(
        current_state=build_layer(),
        available_actions=[
            action_add_x
        ],
    )

    assert possible_actions == [action_add_x]


def test_next_actions_missing_requirements():
    planner = Planner()

    action_add_x = Action(
        name='require_x',
        requirements={'x': True},
        add_effects={},
        delete_effects={},
    )

    possible_actions = planner._calculate_actions(
        current_state=build_layer(),
        available_actions=[
            action_add_x
        ],
    )

    assert possible_actions ==[]


def test_next_actions_noop():
    planner = Planner()

    noop_action = Action(
        name='noop_x',
        requirements={'x'},
        add_effects={'x'},
        delete_effects=set(),
    )

    possible_actions = planner._calculate_actions(
        current_state=build_layer(
            propositions={'x'},
        ),
        available_actions=[],
    )

    assert possible_actions == [noop_action]


@pytest.mark.parametrize(
    'action_a_kwargs, action_b_kwargs', [
        ({'add_effects': {'x'}}, {'delete_effects': {'x'}}),
        ({'delete_effects': {'x'}}, {'add_effects': {'x'}}),
        ({'requirements': {'x'}}, {'delete_effects': {'x'}}),
        ({'delete_effects': {'x'}}, {'requirements': {'x'}}),
        ({'requirements': {'a'}}, {'requirements': {'b'}}),
        ({'requirements': {'b'}}, {'requirements': {'a'}}),
    ])
def test_next_actions_mutex(action_a_kwargs, action_b_kwargs):
    planner = Planner()

    default_action = Action(
        name='default',
        requirements=set(),
        add_effects=set(),
        delete_effects=set(),
    )

    action_a = default_action.copy(
        name='action_a',
        **action_a_kwargs,
    )

    action_b = default_action.copy(
        name='action_b',
        **action_b_kwargs,
    )

    mutex = planner._calculate_actions_mutex(
        previous_state=Layer(
            actions=[],
            propositions=set(),
            mutex_propositions={
                'a': {'b'},
                'b': {'a'},
            }
        ),
        possible_actions=[
            action_a,
            action_b,
        ],
    )

    assert mutex == {
        action_a: {action_b},
        action_b: {action_a},
    }


@pytest.mark.parametrize(
    'action_kwargs, expected_propositions', [
        ({'add_effects': {'x'}}, {'x'}),
        ({'delete_effects': {'x'}}, {'x'}),
        ({'add_effects': {'x'}, 'delete_effects': {'x'}}, {'x'}),
        ({'add_effects': {'x'}, 'delete_effects': {'y'}}, {'x', 'y'}),
    ])
def test_next_propositions(action_kwargs, expected_propositions):
    planner = Planner()

    action = Action(
        name='action',
        requirements=set(),
        add_effects=set(),
        delete_effects=set(),
    )

    action = action.copy(**action_kwargs)

    next_propositions = planner._calculate_propositions(
        previous_state=build_layer(),
        actions=[
            action
        ]
    )

    assert next_propositions == expected_propositions


def test_next_propositions_mutex():
    planner = Planner()

    default_action = Action(
        name='action',
        requirements=set(),
        add_effects=set(),
        delete_effects=set(),
    )

    action_a = default_action.copy(name='action_a', add_effects={'x', 'z'})
    action_b = default_action.copy(name='action_b', add_effects={'y', 'z'})

    mutex_propositions = planner._calculate_propositions_mutex(
        previous_state=build_layer(),
        actions=[
            action_a,
            action_b,
        ],
        mutex_actions={
            action_a: {action_b},
            action_b: {action_a},
        },
    )

    assert mutex_propositions == {
        'x': {'y'}, 'y': {'x'}
    }


@pytest.mark.parametrize(
    'goal, propositions, mutex_propositions, reached',
    [(
        {'x', 'y'}, {'x', 'y'}, {}, True
    ), (
        {'x', 'y'}, {'x', 'y', 'z'}, {'y': {'z'}, 'z': {'y'}}, True
    ), (
        {'x'}, {'x', 'y'}, {}, True
    ), (
        {'x', 'y'}, {'x'}, {}, False
    ), (
        {'x', 'y'}, {'x', 'y'}, {'x': {'y'}, 'y': {'x'}}, False
    )])
def test_goal_reached(propositions, mutex_propositions, goal, reached):
    planner = Planner()

    layer = Layer(
        actions=[],
        mutex_actions={},
        propositions=propositions,
        mutex_propositions=mutex_propositions,
    )

    assert planner._plan_goal_reached(
        layer,
        goal,
    ) == reached


# DONE: calculate plan stalled
# DONE: calculate pre-requisites
# TODO: calculate plan(integration)


@pytest.mark.parametrize(
    'layers, stalled', [(
        [{'propositions': {'x'}}, {'propositions': {'x'}}], True
    ), (
        [{'propositions': {'x'}}, {'propositions': {'x', 'y'}}], False
    )]
)
def test_plan_stalled(layers, stalled):
    planner = Planner()

    layers = [
        build_layer(**layer_args)
        for layer_args in layers
    ]

    assert planner._plan_is_stalled(layers) == stalled


def test_search_goal_actions():
    planner = Planner()

    add_x = Action(
        name='add_x',
        requirements=set(),
        add_effects={'x'},
        delete_effects=set(),
    )
    add_y = Action(
        name='add_y',
        requirements=set(),
        add_effects={'y'},
        delete_effects=set(),
    )
    add_x_mutex = Action(
        name='add_x_mutex',
        requirements=set(),
        add_effects={'y'},
        delete_effects=set(),
    )

    layer = Layer(
        actions=[
            add_x,
            add_y,
            add_x_mutex,
        ],
        propositions={'x', 'y'},
        mutex_actions={add_x: {add_x_mutex}, add_x_mutex: {add_x}},
        mutex_propositions={},
    )

    goal = {'x', 'y'}

    goal_actions = [
        {add_x, add_y},
    ]

    assert list(planner._goal_search_actions(layer, goal)) == goal_actions


def test_calculate_subgoal():
    planner = Planner()

    actions = {
        Action(
            name='pre_x',
            requirements={'pre_x'},
            add_effects=set(),
            delete_effects=set(),
        ),
        Action(
            name='pre_y',
            requirements={'pre_y'},
            add_effects=set(),
            delete_effects=set(),
        )
    }

    expected_subgoal = {'pre_x', 'pre_y'}

    assert planner._goal_calculate_subgoal(actions) == expected_subgoal


def test_plan_simple():
    add_x = Action(
        name='add_x',
        requirements=set(),
        add_effects={'x'},
        delete_effects=set(),
    )

    add_y = Action(
        name='add_y',
        requirements={'x'},
        add_effects={'y'},
        delete_effects=set(),
    )

    replace_x_z = Action(
        name='replace_x_z',
        requirements={'x'},
        add_effects={'z'},
        delete_effects={'x'},
    )

    planner = Planner()

    assert planner.plan(
        state=set(),
        goal={'x', 'y', 'z'},
        actions={
            add_x,
            add_y,
            replace_x_z,
        }
    ) == [
        add_x,
        add_y,
        replace_x_z,
        add_x,
    ]
