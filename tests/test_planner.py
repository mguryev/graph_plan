import pytest

from graph_plan import planner
# from graph_plan.planner import Planner, Action, Layer
# from graph_plan.planner import GraphBuilder, GraphSolver
# from graph_plan.planner import PlanNotFound, PlanNotPossible


def build_layer(**kwargs):
    empty_layer = planner.Layer(
        actions=[],
        propositions=set(),
        mutex_actions={},
        mutex_propositions={},
    )

    return empty_layer.copy(
        **kwargs
    )


def build_action(name, **kwargs):
    action_template = planner.Action(
        name=name,
        requirements=set(),
        effects=set(),
    )

    return action_template.copy(**kwargs)


def test_graph_layer_build_empty():
    builder = planner.GraphBuilder()

    next_layer = builder.calculate_next_layer(
        current_state=build_layer(),
        available_actions=[],
    )

    assert next_layer == planner.Layer(
        actions=[],
        propositions=set(),
    )


def test_graph_layer_add_actions():
    builder = planner.GraphBuilder()

    action_add_x = planner.Action(
        name='add_x',
        requirements=set(),
        effects=set(),
    )

    next_layer = builder.calculate_next_layer(
        current_state=build_layer(),
        available_actions=[
            action_add_x
        ]
    )

    assert next_layer.actions == [action_add_x]


def test_graph_layer_action_requirements():
    builder = planner.GraphBuilder()

    action = planner.Action(
        name='add_x',
        requirements=set('not_met_requirement'),
        effects=set(),
    )

    next_layer = builder.calculate_next_layer(
        current_state=build_layer(),
        available_actions=[
            action
        ]
    )

    assert next_layer == planner.Layer(
        actions=[],
        propositions=set(),
    )


def test_graph_layer_actions_noop():
    builder = planner.GraphBuilder()

    next_layer = builder.calculate_next_layer(
        current_state=build_layer(
            propositions={'x'},
        ),
        available_actions=[],
    )

    noop_action = planner.Action(
        name='noop_x',
        requirements={'x'},
        effects={'x'},
    )

    assert next_layer.actions == [noop_action]


@pytest.mark.parametrize(
    'action_a_kwargs, action_b_kwargs, state_kwargs', [
        ({'effects': {'x'}}, {'effects': {'x__unset'}}, {}),
        ({'effects': {'x__unset'}}, {'effects': {'x'}}, {'propositions': {'x'}}),
        ({'requirements': {'x'}}, {'effects': {'x__unset'}}, {'propositions': {'x'}}),
        ({'effects': {'x__unset'}}, {'requirements': {'x'}}, {'propositions': {'x'}}),
        (
            {'requirements': {'a'}}, {'requirements': {'b'}},
            {'propositions': {'a', 'b'}, 'mutex_propositions': {'a': {'b'}, 'b': {'a'}}}
        ),
    ])
def test_graph_layer_actions_mutex(action_a_kwargs, action_b_kwargs, state_kwargs):
    builder = planner.GraphBuilder()

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
        ({'effects': {'x'}}, {'x'}),
        ({'effects': {'x', 'x__unset'}}, {'x', 'x__unset'}),
    ])
def test_graph_layer_propositions(action_kwargs, expected_propositions):
    builder = planner.GraphBuilder()

    action = build_action('action', **action_kwargs)

    next_layer = builder.calculate_next_layer(
        current_state=build_layer(),
        available_actions=[action]
    )

    assert next_layer.propositions == expected_propositions


def test_graph_layer_propositions_mutex():
    builder = planner.GraphBuilder()

    action_a = build_action(name='action_a', effects={'x', 'y__unset'})
    action_b = build_action(name='action_b', effects={'y', 'x__unset'})

    next_layer = builder.calculate_next_layer(
        current_state=build_layer(),
        available_actions=[
            action_a,
            action_b,
        ]
    )

    assert next_layer.mutex_propositions == {
        'x': {'y', 'x__unset'},
        'y': {'x', 'y__unset'},
        'x__unset': {'x', 'y__unset'},
        'y__unset': {'y', 'x__unset'},
    }


def test_graph_goal_found():
    solver = planner.GraphSolver()

    add_x = build_action(name='add_x', effects={'x'})
    graph = [
        planner.Layer(
            actions=[add_x],
            mutex_actions={},
            propositions={'x'},
            mutex_propositions={},
        )
    ]

    plan = solver.search_for_solution(graph, goal={'x'})

    assert plan == [add_x]


def test_graph_goal_not_found():
    solver = planner.GraphSolver()

    add_x = build_action(name='add_x', effects={'x'})

    graph = [
        planner.Layer(
            actions=[add_x],
            mutex_actions={},
            propositions={'x'},
            mutex_propositions={},
        )
    ]

    with pytest.raises(planner.PlanNotFound):
        solver.search_for_solution(graph, goal={'y'})


def test_graph_goal_not_possible():
    solver = planner.GraphSolver()

    add_x = build_action(name='add_x', effects={'x'})
    graph = [
        planner.Layer(
            actions=[add_x],
            mutex_actions={},
            propositions={'x'},
            mutex_propositions={},
        ),
        planner.Layer(
            actions=[add_x],
            mutex_actions={},
            propositions={'x'},
            mutex_propositions={},
        )
    ]

    with pytest.raises(planner.PlanNotPossible):
        solver.search_for_solution(graph, goal={'y'})


def test_state_from_world():
    world = {
        'x': 'set',
        'y': '',
        'z': False,
    }

    expected = {
        'x', 'y__unset', 'z__unset'
    }

    assert planner.state_from_world(world) == expected


def test_plan_simple():
    add_x = planner.Action(
        name='add_x',
        requirements=set(),
        effects={'x'},
    )

    add_y = planner.Action(
        name='add_y',
        requirements={'x'},
        effects={'y'},
    )

    replace_x_z = planner.Action(
        name='replace_x_z',
        requirements={'x'},
        effects={'z', 'x__unset'},
    )

    _planner = planner.Planner()

    assert _planner.plan(
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
