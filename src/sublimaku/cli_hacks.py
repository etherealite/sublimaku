from collections.abc import Callable
from functools import update_wrapper
from typing import Any

import click

from click import get_current_context
from click_option_group import OptionGroup


provider_group: OptionGroup | None = None

_option = click.option
_group = click.group


def isolate_group_params(
    keyed_func: Callable,
    params: list[click.Parameter],
    providers_config: OptionGroup,
) -> tuple[int, list[(int, click.Parameter)], list[click.Parameter]]:
    """
    Isolate providers_config parameters

    Remove all of the providers_config params and store them.
    return the position of the first found param, the isloated params
    and the remaining params.
    """
    params: list[click.Parameter] = params.copy()
    rest_params: list[click.Parameter] = []
    group_params: list[click.Parameter] = []
    positions: list[int] = []
    for pos, param in enumerate(params):
        if (
            param.name in providers_config._options[keyed_func] or
            param == providers_config._group_title_options[keyed_func]
        ):
            group_params.append(param)
            positions.append(pos)
        else:
            rest_params.append(param)

    start_pos = positions[0]

    return start_pos, group_params, rest_params


def configure_jimaku(*args, **kwargs):
    jimaku_args = kwargs.pop('jimaku')

    ctx = get_current_context()

    provider_configs: dict[str, dict[Any, Any]] = ctx.obj['provider_configs']

    jimaku_config = provider_configs.get('jimaku', {})

    jimaku_config['apikey'] = (
        jimaku_args if jimaku_args else jimaku_config.get('apikey')
    )

    return args, kwargs


def option(*args, **kwargs):
    global provider_group
    # force the download subcommand to use the jimaku provider
    if '--provider' in args:
        provider_manager = globals().get('provider_manager')
        if provider_manager is None:
            from subliminal import provider_manager
        provider_manager.register('jimaku = sublimaku:JimakuProvider')
        kwargs['type'] = click.Choice(sorted(provider_manager.names()))

    # save a copy of the providers_config group so we can add our own
    # options to it later
    if provider_group is None and (group := kwargs.get('group')):
        if isinstance(group, OptionGroup) and group.name == 'Providers configuration':
            provider_group = group

    return _option(*args, **kwargs)


def group(*args, **kwargs):

    click_decorator = _group(*args, **kwargs)

    def decorator(f):
        global provider_group

        (
            start_pos,
            group_params,
            rest_params
        ) = isolate_group_params(
            f.__wrapped__, f.__click_params__, provider_group
        )

        # feed the isolated params into the option group decorator
        # so the we pass the checks for mixing decorators but still
        # make use of their creational logic
        f.__click_params__ = group_params
        f = provider_group.option(
            '--jimaku',
            type=click.STRING,
            nargs=1,
            metavar='APIKEY',
            help='Jimaku configuration.',
        )(f)

        # recombine all of the original params and our new grouped params
        # back together while maintaining sequence.
        group_params = f.__click_params__
        rest_params[start_pos:start_pos] = group_params

        # wrap the cmd group callback yet again so that we can set
        # the context object to contain our own provider config.
        #
        # the cmd group callback will now be wrapped 3 times:
        # @click.pass_context -> new_func -> @click.group
        def new_func(*args, **kwargs):
            args, kwargs = configure_jimaku(*args, **kwargs)
            return f(*args, **kwargs)

        del f.__click_params__
        new_func = update_wrapper(new_func, f)
        new_func.__click_params__ = rest_params

        return click_decorator(new_func)

    return decorator


click.option = option
click.group = group
