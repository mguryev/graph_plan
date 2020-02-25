import collections
import itertools
import logging
import typing

import attr


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


@attr.s
class ActionLayer(object):
    actions = attr.ib(type=typing.List['Action'])
    mutex_actions = attr.ib(type=typing.Dict['Action', typing.Set['Action']], default=attr.Factory(dict))


@attr.s
class PropositionLayer(object):
    propositions = attr.ib(type=typing.Set[str])
    mutex_propositions = attr.ib(type=typing.Dict[str, typing.Set[str]], default=attr.Factory(dict))


PropositionLabel = str


@attr.s
class Layer(object):
    actions = attr.ib(type=typing.List['Action'])
    propositions = attr.ib(type=typing.Set[PropositionLabel])
    mutex_actions = attr.ib(type=typing.Dict['Action', typing.Set['Action']], default=attr.Factory(dict))
    mutex_propositions = attr.ib(type=typing.Dict[PropositionLabel, typing.Set[PropositionLabel]], default=attr.Factory(dict))

    def copy(self, **changes):
        return attr.evolve(self, **changes)


@attr.s(frozen=True)
class Action(object):
    name = attr.ib(type=str)
    requirements = attr.ib(type=typing.Set[PropositionLabel], hash=False)
    add_effects = attr.ib(type=typing.Set[PropositionLabel], hash=False)
    delete_effects = attr.ib(type=typing.Set[PropositionLabel], hash=False)

    def copy(self, **changes):
        return attr.evolve(self, **changes)


class PlanNotFound(BaseException):
    pass


class PlanNotPossible(BaseException):
    pass


class Planner(object):
    @classmethod
    def _action_requirements_met(cls, state: Layer, action: Action):
        log.debug('Validating action requirements for {}'.format(action.name))
        return all(
            proposition in state.propositions
            for proposition in action.requirements
        )

    @classmethod
    def _create_noop_action(cls, proposition) -> Action:
        return Action(
            name=f'noop_{proposition}',
            requirements={proposition},
            add_effects={proposition},
            delete_effects=set(),
        )

    @classmethod
    def _calculate_actions(cls, current_state: Layer, available_actions) -> typing.List[Action]:
        log.info('Generating noop actions')
        noop_actions = [
            cls._create_noop_action(proposition=proposition)
            for proposition in current_state.propositions
        ]

        log.info('Expanding actions')
        next_actions = [
            action
            for action in available_actions
            if cls._action_requirements_met(current_state, action)
        ]

        log.info('Noop actions: %s', noop_actions)
        log.info('Next actions: %s', next_actions)
        return noop_actions + next_actions

    @classmethod
    def _is_action_mutex(cls, mutex_propositions, action_a: Action, action_b: Action):
        log.debug('Checking mutex conditions for %s, %s', action_a, action_b)

        if action_a.delete_effects.intersection(action_b.add_effects):
            log.debug('Action a deletes an effect of action B. Mutex condition found')
            return True

        if action_a.delete_effects.intersection(action_b.requirements):
            log.debug('Action a deletes a precondition of action B. Mutex condition found')
            return True

        action_a_requirement_mutex = set()
        for requirement_proposition in action_a.requirements:
            action_a_requirement_mutex = action_a_requirement_mutex.union(
                mutex_propositions.get(requirement_proposition, set())
            )
        log.debug('Action a requirement mutex list: %s', action_a_requirement_mutex)

        if action_a_requirement_mutex.intersection(action_b.requirements):
            log.debug('Action a requirement is mutually exclusive to action b requirements. Mutex condition found')
            return True

        return False

    @classmethod
    def _calculate_actions_mutex(
        cls,
        previous_state: Layer,
        possible_actions: typing.List[Action],
    ) -> typing.Dict[Action, typing.Set[Action]]:
        mutex = collections.defaultdict(set)

        for action, other_action in itertools.permutations(possible_actions, 2):
            if cls._is_action_mutex(previous_state.mutex_propositions, action, other_action):
                mutex[action].add(other_action)
                mutex[other_action].add(action)

        return mutex

    @classmethod
    def _calculate_propositions(
        cls,
            previous_state: Layer, actions: typing.List[Action],
    ) -> typing.Set[PropositionLabel]:
        propositions = [
            proposition
            for action in actions
            for proposition in action.add_effects.union(action.delete_effects)
        ]
        return set(propositions)

    @classmethod
    def _calculate_propositions_mutex(
        cls,
        previous_state: Layer,
        actions: typing.List[Action],
        mutex_actions: typing.Dict[Action, typing.Set[Action]],
    ) -> typing.Dict[PropositionLabel, typing.Set[PropositionLabel]]:
        prop_actions = collections.defaultdict(list)

        for proposition, action in (
            (proposition, action)
            for action in actions
            for proposition in action.add_effects
        ):
            log.info('Proposition %s - action %s', proposition, action)
            prop_actions[proposition].append(action)

        log.info('Mutex actions: %s', mutex_actions)

        propositions = list(prop_actions.keys())
        proposition_mutex = collections.defaultdict(set)

        for this_prop, mutex_prop in itertools.combinations(propositions, 2):
            log.info('Checking action mutexes for %s - %s', this_prop, mutex_prop)

            actions_mutexes = (
                action_b in mutex_actions[action_a]
                for action_a in prop_actions[this_prop]
                for action_b in prop_actions[mutex_prop]
            )

            if all(actions_mutexes):
                log.info('Propositions are mutex!')
                proposition_mutex[this_prop].add(mutex_prop)
                proposition_mutex[mutex_prop].add(this_prop)

        return dict(proposition_mutex)

    def calculate_next_layer(self, current_state: Layer, available_actions) -> Layer:
        next_actions = self._calculate_actions(current_state, available_actions)
        mutex_actions = self._calculate_actions_mutex(current_state, next_actions)
        next_propositions = self._calculate_propositions(current_state, next_actions)
        mutex_propositions = self._calculate_propositions_mutex(current_state, next_actions, mutex_actions)

        return Layer(
            actions=next_actions,
            mutex_actions=mutex_actions,
            propositions=next_propositions,
            mutex_propositions=mutex_propositions,
        )

    def _plan_goal_reached(
        self,
        # propositions: typing.Set[PropositionLabel],
        # mutex_propositions: typing.Dict[PropositionLabel, typing.Set[PropositionLabel]],
        layer: Layer,
        goal: typing.Set[PropositionLabel],
    ):
        log.info('Checking if goal is reached: %s', goal)

        propositions = layer.propositions
        mutex_propositions = layer.mutex_propositions
        log.info('Current propositions: %s', propositions)
        log.info('Current mutex propositions: %s', mutex_propositions)

        if not goal.issubset(propositions):
            log.info('not every goal proposition is met')
            return False

        if any((
            goal.intersection(mutex_propositions.get(proposition, set()))
            for proposition in goal
        )):
            log.info('goal propositions are mutex')
            return False

        return True

    def _plan_is_stalled(self, layers: typing.List[Layer]):
        log.info('Checking if plan has stalled')

        return layers[-1] == layers[-2]

    def _goal_is_action_set_mutex(
        self, action_mutex: typing.Dict['Action', typing.Set['Action']], *actions: typing.List[Action]
    ):
        return any(
            action_b in action_mutex.get(action_a, set())
            for (action_a, action_b) in itertools.combinations(actions, 2)
        )

    def _goal_search_actions(
        self, layer: Layer, goal: typing.Set[PropositionLabel]
    ) -> typing.Iterable[typing.Set[Action]]:
        log.info('Checking if goal is reached: %s', goal)

        propositions = layer.propositions
        mutex_actions = layer.mutex_actions
        log.info('Current propositions: %s', propositions)

        prop_actions = collections.defaultdict(list)

        for proposition, action in (
            (proposition, action)
            for action in layer.actions
            for proposition in action.add_effects
        ):
            log.info('Proposition %s - action %s', proposition, action)
            prop_actions[proposition].append(action)

        goal_actions = [
            prop_actions[proposition]
            for proposition in goal
        ]

        return (
            set(action_set)
            for action_set in itertools.product(*goal_actions)
            if not self._goal_is_action_set_mutex(mutex_actions, *action_set)
        )

    def _goal_calculate_subgoal(
        self, actions: typing.Set[Action]
    ) -> typing.Set[PropositionLabel]:
        return {
            proposition
            for action in actions
            for proposition in action.requirements
        }

    def _search_for_solution(
        self, layers: typing.List[Layer], goal: typing.Set[PropositionLabel]
    ) -> typing.List[Action]:
        log.info('Searching for solution for goal: %s', goal)

        if goal == set():
            log.info('Goal is achieved!')
            return []

        current_layer = layers[-1]
        log.info('Current layer: %s', current_layer)

        if not self._plan_goal_reached(current_layer, goal):
            log.info('Goal is not reached in the current layer. Solution is not found')
            raise PlanNotFound()

        log.info('Searching for action sets that can achieve the goal')
        for goal_actions in self._goal_search_actions(current_layer, goal):
            log.info('Attempting action set: %s', goal_actions)

            sub_goal = self._goal_calculate_subgoal(goal_actions)
            log.info('Sub-goal: %s', sub_goal)

            try:
                subgoal_actions = self._search_for_solution(layers[:-1], sub_goal)

            except PlanNotFound:
                log.info('No plan found in action set')
                continue

            plan_actions = subgoal_actions + list(goal_actions)
            break

        else:
            log.info('Ran out of action sets. Solution is not found')
            raise PlanNotFound()

        log.info('Plan is found!')
        return plan_actions

    def plan(
            self,
            state: typing.Set[PropositionLabel],
            goal: typing.Set[PropositionLabel],
            actions: typing.Set[Action],
    ) -> typing.List[Action]:
        log.info('Starting to search for plan')

        plan_possible = True
        layers = [
            Layer(
                actions=[],
                mutex_actions={},
                propositions=state,
                mutex_propositions={},
            )
        ]

        plan = []

        while plan_possible:
            log.info('Attempting to find solution by adding a layer')
            current_layer = layers[-1]

            log.info('Current layer: %s', current_layer)
            next_layer = self.calculate_next_layer(current_layer, actions)

            log.info('Next layer: %s', next_layer)
            layers += [next_layer]

            plan_possible = not self._plan_is_stalled(layers)
            log.info('Is plan possible: %s', plan_possible)

            try:
                log.info('Searching for plan in current layers')
                plan = self._search_for_solution(layers, goal)
                break

            except PlanNotFound:
                log.info('Plan not found in current layers')

        if not plan_possible:
            log.info('Plan does not seem to be possible')
            raise PlanNotPossible

        return [
            action
            for action in plan
            if not action.name.startswith('noop_')
        ]
