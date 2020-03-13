import pytest

from .planner import Planner, Action, Layer
from .planner import GraphBuilder, GraphSolver
from .planner import PlanNotFound, PlanNotPossible


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


def test_graph_goal_found():
    add_x = build_action(name='add_x', add_effects={'x'})

    graph = [
        Layer(
            actions=[add_x],
            mutex_actions={},
            propositions={'x'},
            mutex_propositions={},
        )
    ]
    goal = {'x'}

    solver = GraphSolver()

    plan = solver.search_for_solution(graph, goal)

    assert plan == [add_x]


def test_graph_goal_not_found():
    add_x = build_action(name='add_x', add_effects={'x'})

    graph = [
        Layer(
            actions=[add_x],
            mutex_actions={},
            propositions={'x'},
            mutex_propositions={},
        )
    ]
    goal = {'y'}

    solver = GraphSolver()

    with pytest.raises(PlanNotFound):
        solver.search_for_solution(graph, goal)


def test_graph_goal_not_possible():
    add_x = build_action(name='add_x', add_effects={'x'})

    graph = [
        Layer(
            actions=[add_x],
            mutex_actions={},
            propositions={'x'},
            mutex_propositions={},
        ),
        Layer(
            actions=[add_x],
            mutex_actions={},
            propositions={'x'},
            mutex_propositions={},
        )
    ]
    goal = {'y'}

    solver = GraphSolver()

    with pytest.raises(PlanNotPossible):
        solver.search_for_solution(graph, goal)


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
