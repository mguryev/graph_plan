import graph_plan


def run():
    host = {
        'ip_address': '169.254.169.1',
        'ip_address_ipmi': '',
        'downtime': False,
    }

    starting_state = graph_plan.state_from_world(host)

    desired_state = {
        'status__in-service'
    }

    actions = [
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

    planner = graph_plan.Planner()

    plan = planner.plan(
        state=starting_state,
        goal=desired_state,
        actions=set(actions),
    )

    print('=====')

    print(f'Starting state: {starting_state}')
    print('=====')

    print(f'Desired state: {desired_state}')
    print('=====')

    print('Available actions:\n')
    for action in actions:
        print(f'name: {action.name}')
        print(f'requirements: {sorted(action.requirements)}')
        print(f'add_effects: {sorted(action.effects)}')
        print('')
    print('=====')

    print('Plan:')
    for action in plan:
        print(f'{action.name}')


if __name__ == '__main__':
    run()
