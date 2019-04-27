"""
Acceptor
========

Acceptors handle the acceptance step. Stochastic acceptors make use of
temperature schemes and pdf_max_eval methods.

"""


from .acceptor import (
    Acceptor,
    SimpleFunctionAcceptor,
    accept_uniform_use_current_time,
    accept_uniform_use_complete_history,
    UniformAcceptor,
    StochasticAcceptor,)
from .temperature_scheme import (
    scheme_acceptance_rate,
    scheme_polynomial_decay,
    scheme_exponential_decay,
    scheme_daly,
    scheme_ess,
    scheme_friel_pettitt,)
from .pdf_max_eval import (
    pdf_max_take_from_kernel,
    pdf_max_take_max_found,)


__all__ = [
    # acceptor
    'Acceptor',
    'SimpleFunctionAcceptor',
    'accept_uniform_use_current_time',
    'accept_uniform_use_complete_history',
    'UniformAcceptor',
    'StochasticAcceptor',
    # temperature scheme
    'scheme_acceptance_rate',
    'scheme_polynomial_decay',
    'scheme_exponential_decay',
    'scheme_daly',
    'scheme_ess',
    'scheme_friel_pettitt',
    # pdf max eval
    'pdf_max_take_from_kernel',
    'pdf_max_take_max_found',
]
