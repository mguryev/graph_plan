import pytest

from .planner import Planner, Action, Layer
from .planner import GraphBuilder


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


def build_action(name, **kwargs):
    action_template = Action(
        name=name,
        requirements=set(),
        add_effects=set(),
        delete_effects=set(),
    )

    return action_template.copy(**kwargs)


def test_graph_layer_build_empty():
    builder = GraphBuilder()

    next_layer = builder.calculate_next_layer(
        current_state=build_layer(),
        available_actions=[],
    )

    assert next_layer == Layer(
        actions=[],
        propositions=set(),
    )


def test_graph_layer_add_actions():
    builder = GraphBuilder()

    action_add_x = Action(
        name='add_x',
        requirements=set(),
        add_effects=set(),
        delete_effects=set(),
    )

    next_layer = builder.calculate_next_layer(
        current_state=build_layer(),
        available_actions=[
            action_add_x
        ]
    )

    assert next_layer.actions == [action_add_x]


def test_graph_layer_action_requirements():
    builder = GraphBuilder()

    action = Action(
        name='add_x',
        requirements=set('not_met_requirement'),
        add_effects=set(),
        delete_effects=set(),
    )

    next_layer = builder.calculate_next_layer(
        current_state=build_layer(),
        available_actions=[
            action
        ]
    )

    assert next_layer == Layer(
        actions=[],
        propositions=set(),
    )


def test_graph_layer_actions_noop():
    builder = GraphBuilder()

    next_layer = builder.calculate_next_layer(
        current_state=build_layer(
            propositions={'x'},
        ),
        available_actions=[],
    )

    noop_action = Action(
        name='noop_x',
        requirements={'x'},
        add_effects={'x'},
        delete_effects=set(),
    )

    assert next_layer.actions == [noop_action]


@pytest.mark.parametrize(
    'action_a_kwargs, action_b_kwargs, state_kwargs', [
        ({'add_effects': {'x'}}, {'delete_effects': {'x'}}, {}),
        ({'delete_effects': {'x'}}, {'add_effects': {'x'}}, {'propositions': {'x'}}),
        ({'requirements': {'x'}}, {'delete_effects': {'x'}}, {'propositions': {'x'}}),
        ({'delete_effects': {'x'}}, {'requirements': {'x'}}, {'propositions': {'x'}}),
        (
            {'requirements': {'a'}}, {'requirements': {'b'}},
            {'propositions': {'a', 'b'}, 'mutex_propositions': {'a': {'b'}, 'b': {'a'}}}
        ),
    ])
def test_graph_layer_actions_mutex(action_a_kwargs, action_b_kwargs, state_kwargs):
    builder = GraphBuilder()

    action_a = build_action(name='action_a', **action_a_kwargs)
    action_b = build_action(name='action_b', **action_b_kwargs)

    next_layer = builder.calculate_next_layer(
        current_state=build_layer(**state_kwargs),
        available_actions=[
            action_a,
            action_b,
        ],
    )

    assert (
        action_b in next_layer.mutex_actions.get(action_a)
        and action_a in next_layer.mutex_actions.get(action_b)
    )


@pytest.mark.parametrize(
    'action_kwargs, expected_propositions', [
        ({'add_effects': {'x'}}, {'x'}),
        ({'delete_effects': {'x'}}, {'x'}),
        ({'add_effects': {'x'}, 'delete_effects': {'x'}}, {'x'}),
        ({'add_effects': {'x'}, 'delete_effects': {'y'}}, {'x', 'y'}),
    ])
def test_graph_layer_propositions(action_kwargs, expected_propositions):
    builder = GraphBuilder()

    action = build_action('action', **action_kwargs)

    next_layer = builder.calculate_next_layer(
        current_state=build_layer(),
        available_actions=[action]
    )

    assert next_layer.propositions == expected_propositions


def test_graph_layer_propositions_mutex():
    builder = GraphBuilder()

    action_a = build_action(name='action_a', add_effects={'x', 'z'}, delete_effects={'y'})
    action_b = build_action(name='action_b', add_effects={'y', 'z'}, delete_effects={'x'})

    next_layer = builder.calculate_next_layer(
        current_state=build_layer(),
        available_actions=[
            action_a,
            action_b,
        ]
    )

    assert next_layer.mutex_propositions == {
        'x': {'y'}, 'y': {'x'}
    }


# def test_extend_graph():
#     builder = GraphBuilder()
#
#     next_layer = builder.extend_graph(
#         current_state=build_layer(),
#         available_actions=[],
#     )
#
#     assert next_layer == Layer(
#         actions=[],
#         propositions=set(),
#     )


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
        replace_x_z,
        add_x,
        add_y,
    ]
