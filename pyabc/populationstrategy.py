"""
Population stratgy
==================

Strategies to choose the population size.

At the moment, only constant population size is supported. But this might
change in the future.
"""

import numpy as np
import logging
import json
import warnings
from typing import List
from .transition import Transition
from .transition.predict_population_size import predict_population_size
adaptation_logger = logging.getLogger("Adaptation")


class PopulationStrategy:
    """
    Size of the diffrent populations

    This is a non-functional base implementation. Do not use this class
    directly. Subclasses must override the `adapt_population_size` method.

    Parameters
    ----------

    nr_particles: int
       Number of particles per populations

    nr_populations: int
        Maximum number of populations

    nr_samples_per_parameter: int
        Number of samples to draw for a proposed parameter
    """
    def __init__(self, nr_particles: int, nr_populations: int,
                 nr_samples_per_parameter: int=1):
        self.nr_particles = nr_particles
        self.nr_populations = nr_populations
        self.nr_samples_per_parameter = nr_samples_per_parameter

    def adapt_population_size(self, transitions: List[Transition],
                              model_weights: np.ndarray):
        """

        Parameters
        ----------
        transitions
        model_weights

        Returns
        -------

        """
        raise NotImplementedError

    def get_config(self):
        """
        Returns
        -------
        dict
            Configuration of the class as dictionary
        """
        return {"name": self.__class__.__name__,
                "nr_particles": self.nr_particles,
                "nr_populations": self.nr_populations}

    def to_json(self):
        """
        Returns
        -------

        str
            Configuration of the class as json string.
        """
        return json.dumps(self.get_config())


class ConstantPopulationStrategy(PopulationStrategy):
    """
    Constant size of the diffrent populations

    Parameters
    ----------

    nr_particles: int
       Number of particles per populations

    nr_populations: int
        Maximum number of populations

    nr_samples_per_parameter: int
        Number of samples to draw for a proposed parameter
    """
    def adapt_population_size(self, transitions, model_weights):
        pass


class AdaptivePopulationStrategy(PopulationStrategy):
    """
    Adapt the population size according to the mean coefficient of variation
    error criterion.

    Parameters
    ----------

    nr_particles: int
        Number of particles in the first populations

    nr_populations: int
        Max number of populations

    mean_cv: float, optional
        The error criterion. Defaults to 0.05.
        A smaller value leads generally to larger populations.
        The error criterion is the mean coefficient of variation of
         the estimated KDE.

    nr_samples_per_parameter: int, optional
        Defaults to 1.

    max_population_size: int, optional
        Max nr of allowe particles in a population.
        Defaults to infinity.

    min_population_size: int, optional
        Min number of particles allowed in a population.
        Defaults to 10
    """
    def __init__(self, nr_particles, nr_populations,
                 nr_samples_per_parameter=1,
                 mean_cv=0.05, max_population_size=float("inf"),
                 min_population_size=10):
        warnings.warn("Adaptive population strategy is experimental.")
        super().__init__(nr_particles, nr_populations,
                         nr_samples_per_parameter)
        self.max_population_size = max_population_size
        self.min_population_size = min_population_size
        self.mean_cv = mean_cv

    def get_config(self):
        return {"name": self.__class__.__name__,
                "max_population_size": self.max_population_size,
                "mean_cv": self.mean_cv}

    def adapt_population_size(self, transitions: List[Transition],
                              model_weights: np.ndarray):
        def calc_cv(nr_particles):
            cv = sum(
                w * transition.mean_cv(
                    np.round(nr_particles * w).astype(int))
                for transition, w in
                zip(transitions, model_weights))
            return float(cv)

        old_particles = self.nr_particles
        cv_estimate = predict_population_size(old_particles,
                                              self.mean_cv,
                                              calc_cv)

        self.nr_particles = max(min(int(cv_estimate.n_estimated),
                                    self.max_population_size),
                                self.min_population_size)

        adaptation_logger.debug("Change nr particles {} -> {}"
                                .format(old_particles, self.nr_particles))
