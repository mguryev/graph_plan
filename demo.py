import graph_plan


ACTIONS = [
    graph_plan.Action(
        name='reserve_ip_address',
        requirements=set(),
        effects={'ip_address'},
    ),
    graph_plan.Action(
        name='reserve_ip_address_ipmi',
        requirements=set(),
        effects={'ip_address_ipmi'},
    ),
    graph_plan.Action(
        name='create_dns_record',
        requirements={'ip_address'},
        effects={'dns_record'},
    ),
    graph_plan.Action(
        name='create_dns_record_ipmi',
        requirements={'ip_address_ipmi'},
        effects={'dns_record_ipmi'},
    ),
    graph_plan.Action(
        name='set_downtime',
        requirements=set(),
        effects={'downtime'},
    ),
    graph_plan.Action(
        name='remove_downtime',
        requirements={'downtime'},
        effects={'downtime__unset'},
    ),
    graph_plan.Action(
        name='reimage',
        requirements={
            'ip_address',
            'dns_record',
            'dns_record_ipmi',
            'downtime',
        },
        effects={'image'},
    ),
    graph_plan.Action(
        name='set_in_service',
        requirements={
            'image',
            'downtime__unset',
        },
        effects={'status__in-service'},
    ),
]


def describe_actions():
    print('Available actions:')
    print('')

    for action in ACTIONS:
        print(f'name: {action.name}')
        print(f'requirements: {sorted(action.requirements)}')
        print(f'add_effects: {sorted(action.effects)}')
        print('')
    print('=====')


def demo1():
    print('=====')
    print('Demo 1: calculating a plan')
    print('=====')

    host = {
        'ip_address': '169.254.169.1',
        'ip_address_ipmi': '',
        'downtime': False,
    }

    starting_state = graph_plan.state_from_world(host)
    print('')
    print(f'Starting state: {starting_state}')
    print('=====')

    desired_state = {
        'status__in-service'
    }
    print('')
    print(f'Desired state: {desired_state}')
    print('=====')

    describe_actions()

    planner = graph_plan.Planner()

    plan = planner.plan(
        state=starting_state,
        goal=desired_state,
        actions=set(ACTIONS),
    )

    print('Plan:')
    print('')
    for action in plan:
        print(f'{action.name}')

    print('')


def demo2():
    print('=====')
    print('Demo 2: updating state - multiple dependent actions')
    print('=====')

    host = {
        'ip_address': '169.254.169.1',
        'ip_address_ipmi': '169.254.169.2',
        'dns_record': 'host1.hostname.com',
        'dns_record_ipmi': 'host1-ipmi.hostname.com',
        'image': 'image.345',
        'downtime': False,
    }

    starting_state = graph_plan.state_from_world(host)
    print('')
    print(f'Starting state: {starting_state}')
    print('=====')

    update = {
        'ip_address'
    }
    print('')
    print(f'Desired update: {update}')
    print('=====')

    describe_actions()

    planner = graph_plan.Planner()

    plan = planner.plan_state_update(
        state=starting_state,
        update=update,
        actions=set(ACTIONS),
    )

    print('Plan:')
    print('')
    for action in plan:
        print(f'{action.name}')

    print('')


def demo3():
    print('=====')
    print('Demo 3: updating state - retaining state')
    print('=====')

    host = {
        'ip_address': '169.254.169.1',
        'ip_address_ipmi': '169.254.169.2',
        'dns_record': 'host1.hostname.com',
        'dns_record_ipmi': 'host1-ipmi.hostname.com',
        'image': 'image.345',
        'downtime': False,
    }

    starting_state = graph_plan.state_from_world(host)
    print('')
    print(f'Starting state: {starting_state}')
    print('=====')

    update = {
        'ip_address_ipmi'
    }
    print('')
    print(f'Desired update: {update}')
    print('=====')

    describe_actions()

    planner = graph_plan.Planner()

    plan = planner.plan_state_update(
        state=starting_state,
        update={'ip_address_ipmi'},
        actions=set(ACTIONS),
    )
    print('Plan:')
    print('')
    for action in plan:
        print(f'{action.name}')

    print('')


if __name__ == '__main__':
    demo1()
    demo2()
    demo3()
