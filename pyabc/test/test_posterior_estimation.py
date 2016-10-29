import unittest
from pyabc import (ABCSMC, RV, ModelPerturbationKernel, Distribution,
                    MedianEpsilon, Kernel, MinMaxDistanceFunction, PercentileDistanceFunction)
import random
import os
import scipy.stats as st
from scipy.special import gamma, binom
import scipy as sp
import scipy.interpolate
import tempfile



def mean_and_std(values, weights):
    mean = (values * weights).sum()
    std = sp.sqrt(((values - mean)**2 * weights).sum())
    return mean, std


class TestABC(unittest.TestCase):
    def setUp(self):
        self.db_file_location = os.path.join(tempfile.gettempdir(), "abc_unittest_db.db")
        self.db = "sqlite:///" + self.db_file_location
        self.clean_db()

    def clean_db(self):
        try:
            os.remove(self.db_file_location)
        except FileNotFoundError:
            pass

    def tearDown(self):
        self.clean_db()


class TestABCFast(TestABC):
    def test_cookie_jar(self):
        def make_model(theta):
            def model(args):
                return {"result": 1 if random.random() > theta else 0}
            return model

        theta1 = .2
        theta2 = .6
        model1 = make_model(theta1)
        model2 = make_model(theta2)
        models = [model1, model2]
        model_prior = RV("randint", 0, 2)
        nr_particles = 1500
        parameter_given_model_prior_distribution = [Distribution(), Distribution()]
        parameter_perturbation_kernels = [lambda t, stat: Kernel(stat['cov']) for _ in range(2)]
        abc = ABCSMC(models, model_prior, ModelPerturbationKernel(2, probability_to_stay=.8),
                     parameter_given_model_prior_distribution, parameter_perturbation_kernels,
                     MinMaxDistanceFunction(measures_to_use=["result"]), MedianEpsilon(.1), nr_particles)

        model_names = ["m1", "m2"]
        options = {'db_path': self.db}
        abc.set_data({"result": 0}, 0, {}, options, model_names)

        minimum_epsilon = .2
        nr_samples_per_particles = [1] * 3
        history = abc.run(nr_samples_per_particles, minimum_epsilon)
        p1, p2 = history.get_model_probabilities()
        expected_p1, expected_p2 = theta1 / (theta1 + theta2), theta2 / (theta1 + theta2)
        self.assertLess(abs(p1 - expected_p1) + abs(p2 - expected_p2), .05)


    def test_empty_population(self):
        def make_model(theta):
            def model(args):
                return {"result": 1 if random.random() > theta else 0}

            return model

        theta1 = .2
        theta2 = .6
        model1 = make_model(theta1)
        model2 = make_model(theta2)
        models = [model1, model2]
        model_prior = RV("randint", 0, 2)
        nr_particles = 1500
        parameter_given_model_prior_distribution = [Distribution(), Distribution()]
        parameter_perturbation_kernels = [lambda t, stat: Kernel(stat['cov']) for _ in range(2)]
        abc = ABCSMC(models, model_prior, ModelPerturbationKernel(2, probability_to_stay=.8),
                     parameter_given_model_prior_distribution, parameter_perturbation_kernels,
                     MinMaxDistanceFunction(measures_to_use=["result"]), MedianEpsilon(0), nr_particles)

        model_names = ["m1", "m2"]
        options = {'db_path': self.db}
        abc.set_data({"result": 0}, 0, {}, options, model_names)

        minimum_epsilon = -1
        nr_samples_per_particles = [1] * 3
        history = abc.run(nr_samples_per_particles, minimum_epsilon)
        p1, p2 = history.get_model_probabilities()
        expected_p1, expected_p2 = theta1 / (theta1 + theta2), theta2 / (theta1 + theta2)
        self.assertLess(abs(p1 - expected_p1) + abs(p2 - expected_p2), .05)

    def test_beta_binomial_two_identical_models(self):
        binomial_n = 5

        def model(args):
            return {"result": st.binom(binomial_n, args['theta']).rvs()}

        models = [model for _ in range(2)]
        model_prior = RV("randint", 0, 2)
        nr_particles = 800
        parameter_given_model_prior_distribution = [Distribution(theta=RV("beta", 1, 1)) for _ in range(2)]
        parameter_perturbation_kernels = [lambda t, stat: Kernel(stat['cov']) for _ in range(2)]
        abc = ABCSMC(models, model_prior, ModelPerturbationKernel(2, probability_to_stay=.8),
                     parameter_given_model_prior_distribution, parameter_perturbation_kernels,
                     MinMaxDistanceFunction(measures_to_use=["result"]), MedianEpsilon(.1), nr_particles)

        model_names = ["m1", "m2"]
        options = {'db_path': self.db}
        abc.set_data({"result": 2}, 0, {}, options, model_names)

        minimum_epsilon = .2
        nr_samples_per_particles = [1] * 3
        history = abc.run(nr_samples_per_particles, minimum_epsilon)
        p1, p2 = history.get_model_probabilities()
        self.assertLess(abs(p1 - .5) + abs(p2 - .5), .08)


    def test_beta_binomial_different_priors(self):
        binomial_n = 5

        def model(args):
            return {"result": st.binom(binomial_n, args['theta']).rvs()}

        models = [model for _ in range(2)]
        model_prior = RV("randint", 0, 2)
        nr_particles = 800
        a1, b1 = 1, 1
        a2, b2 = 10, 1
        parameter_given_model_prior_distribution = [Distribution(theta=RV("beta", a1, b1)),
                                                    Distribution(theta=RV("beta", a2, b2))]
        parameter_perturbation_kernels = [lambda t, stat: Kernel(stat['cov']) for _ in range(2)]
        abc = ABCSMC(models, model_prior, ModelPerturbationKernel(2, probability_to_stay=.8),
                     parameter_given_model_prior_distribution, parameter_perturbation_kernels,
                     MinMaxDistanceFunction(measures_to_use=["result"]), MedianEpsilon(.1), nr_particles)

        model_names = ["m1", "m2"]
        options = {'db_path': self.db}
        n1 = 2
        abc.set_data({"result": n1}, 0, {}, options, model_names)

        minimum_epsilon = .2
        nr_samples_per_particles = [1] * 3
        history = abc.run(nr_samples_per_particles, minimum_epsilon)
        p1, p2 = history.get_model_probabilities()

        def B(a, b):
            return gamma(a) * gamma(b) / gamma(a + b)

        def expected_p(a, b, n1):
            return binom(binomial_n, n1) * B(a + n1, b + binomial_n - n1) / B(a, b)

        p1_expected_unnormalized = expected_p(a1, b1, n1)
        p2_expected_unnormalized = expected_p(a2, b2, n1)
        p1_expected = p1_expected_unnormalized / (p1_expected_unnormalized+p2_expected_unnormalized)
        p2_expected = p2_expected_unnormalized / (p1_expected_unnormalized+p2_expected_unnormalized)
        self.assertLess(abs(p1 - p1_expected) + abs(p2 - p2_expected), .08)


    def test_beta_binomial_different_priors_initial_epsilon_from_sample(self):
        binomial_n = 5

        def model(args):
            return {"result": st.binom(binomial_n, args['theta']).rvs()}

        models = [model for _ in range(2)]
        model_prior = RV("randint", 0, 2)
        nr_particles = 500
        a1, b1 = 1, 1
        a2, b2 = 10, 1
        parameter_given_model_prior_distribution = [Distribution(theta=RV("beta", a1, b1)),
                                                    Distribution(theta=RV("beta", a2, b2))]
        parameter_perturbation_kernels = [lambda t, stat: Kernel(stat['cov']) for _ in range(2)]
        abc = ABCSMC(models, model_prior, ModelPerturbationKernel(2, probability_to_stay=.8),
                     parameter_given_model_prior_distribution, parameter_perturbation_kernels,
                     MinMaxDistanceFunction(measures_to_use=["result"]), MedianEpsilon(median_multiplier=.9), nr_particles)

        model_names = ["m1", "m2"]
        options = {'db_path': self.db}
        n1 = 2
        abc.set_data({"result": n1}, 0, {}, options, model_names)

        minimum_epsilon = -1
        nr_samples_per_particles = [1] * 5
        history = abc.run(nr_samples_per_particles, minimum_epsilon)
        p1, p2 = history.get_model_probabilities()

        def B(a, b):
            return gamma(a) * gamma(b) / gamma(a + b)

        def expected_p(a, b, n1):
            return binom(binomial_n, n1) * B(a + n1, b + binomial_n - n1) / B(a, b)

        p1_expected_unnormalized = expected_p(a1, b1, n1)
        p2_expected_unnormalized = expected_p(a2, b2, n1)
        p1_expected = p1_expected_unnormalized / (p1_expected_unnormalized + p2_expected_unnormalized)
        p2_expected = p2_expected_unnormalized / (p1_expected_unnormalized + p2_expected_unnormalized)
        self.assertLess(abs(p1 - p1_expected) + abs(p2 - p2_expected), .08)

    def test_continuous_non_gaussian(self):
        def model(args):
            return {"result": sp.rand() * args['u']}

        models = [model]
        model_prior = RV("randint", 0, 1)
        nr_particles = 250
        parameter_given_model_prior_distribution = [Distribution(u=RV("uniform", 0, 1))]
        parameter_perturbation_kernels = [lambda t, stat: Kernel(stat['cov'])]
        abc = ABCSMC(models, model_prior, ModelPerturbationKernel(1, probability_to_stay=1),
                     parameter_given_model_prior_distribution, parameter_perturbation_kernels,
                     PercentileDistanceFunction(measures_to_use=["result"]), MedianEpsilon(.2), nr_particles,
                     max_nr_allowed_sample_attempts_per_particle=2000)

        model_names = ["m1"]
        options = {'db_path': self.db}
        d_observed = .5
        abc.set_data({"result": d_observed}, 0, {}, options, model_names)
        abc.do_not_stop_when_only_single_model_alive()

        minimum_epsilon = -1
        nr_samples_per_particles = [1] * 2
        history = abc.run(nr_samples_per_particles, minimum_epsilon)
        posterior_x, posterior_weight = history.get_results_distribution(0, "u")
        sort_indices = sp.argsort(posterior_x)
        f_empirical = sp.interpolate.interp1d(sp.hstack((-200, posterior_x[sort_indices], 200)),
                                              sp.hstack((0, sp.cumsum(posterior_weight[sort_indices]), 1)))

        @sp.vectorize
        def f_expected(u):
            return (sp.log(u)-sp.log(d_observed)) / (- sp.log(d_observed)) * (u > d_observed)

        x = sp.linspace(0.1, 1)
        max_distribution_difference = sp.absolute(f_empirical(x) - f_expected(x)).max()
        self.assertLess(max_distribution_difference, 0.08)



class TestABCSlow(TestABC):
    def test_gaussian_single_population(self):
        sigma_prior = 1
        sigma_ground_truth = 1
        observed_data = 1

        def model(args):
            return {"y": st.norm(args['x'], sigma_ground_truth).rvs()}

        models = [model]
        model_prior = RV("randint", 0, 1)
        nr_particles = 600
        parameter_given_model_prior_distribution = [Distribution(x=RV("norm", 0, sigma_prior))]
        parameter_perturbation_kernels = [lambda t, stat: Kernel(stat['cov'])]
        abc = ABCSMC(models, model_prior, ModelPerturbationKernel(1, probability_to_stay=1),
                     parameter_given_model_prior_distribution, parameter_perturbation_kernels,
                     PercentileDistanceFunction(measures_to_use=["y"]), MedianEpsilon(.1), nr_particles,
                     max_nr_allowed_sample_attempts_per_particle=2000)

        model_names = ["m1"]
        options = {'db_path': self.db}
        abc.set_data({"y": observed_data}, 0, {}, options, model_names)

        minimum_epsilon = -1
        nr_populations = 1
        nr_samples_per_particles = [1] * nr_populations
        abc.do_not_stop_when_only_single_model_alive()
        history = abc.run(nr_samples_per_particles, minimum_epsilon)
        posterior_x, posterior_weight = history.get_results_distribution(0, "x")
        sort_indices = sp.argsort(posterior_x)
        f_empirical = sp.interpolate.interp1d(sp.hstack((-200, posterior_x[sort_indices], 200)),
                                              sp.hstack((0, sp.cumsum(posterior_weight[sort_indices]), 1)))

        sigma_x_given_y = 1 / sp.sqrt(1 / sigma_prior**2 + 1 / sigma_ground_truth**2)
        mu_x_given_y = sigma_x_given_y**2 * observed_data / sigma_ground_truth**2
        expected_posterior_x = st.norm(mu_x_given_y, sigma_x_given_y)
        x = sp.linspace(-8, 8)
        max_distribution_difference = sp.absolute(f_empirical(x) - expected_posterior_x.cdf(x)).max()
        self.assertLess(max_distribution_difference, 0.12)
        self.assertEqual(history.t, nr_populations)
        mean_emp, std_emp = mean_and_std(posterior_x, posterior_weight)
        self.assertLess(abs(mean_emp - mu_x_given_y), .07)
        self.assertLess(abs(std_emp - sigma_x_given_y), .1)

    def test_gaussian_multiple_populations(self):
        sigma_x = 1
        sigma_y = .5
        y_observed = 2

        def model(args):
            return {"y": st.norm(args['x'], sigma_y).rvs()}

        models = [model]
        model_prior = RV("randint", 0, 1)
        nr_particles = 600
        parameter_given_model_prior_distribution = [Distribution(x=RV("norm", 0, sigma_x))]
        parameter_perturbation_kernels = [lambda t, stat: Kernel(stat['cov'])]
        abc = ABCSMC(models, model_prior, ModelPerturbationKernel(1, probability_to_stay=1),
                     parameter_given_model_prior_distribution, parameter_perturbation_kernels,
                     PercentileDistanceFunction(measures_to_use=["y"]), MedianEpsilon(.2), nr_particles,
                     max_nr_allowed_sample_attempts_per_particle=2000)

        model_names = ["m1"]
        options = {'db_path': self.db}
        abc.set_data({"y": y_observed}, 0, {}, options, model_names)

        minimum_epsilon = -1
        nr_populations = 3
        nr_samples_per_particles = [1] * nr_populations
        abc.do_not_stop_when_only_single_model_alive()
        history = abc.run(nr_samples_per_particles, minimum_epsilon)
        posterior_x, posterior_weight = history.get_results_distribution(0, "x")
        sort_indices = sp.argsort(posterior_x)
        f_empirical = sp.interpolate.interp1d(sp.hstack((-200, posterior_x[sort_indices], 200)),
                                              sp.hstack((0, sp.cumsum(posterior_weight[sort_indices]), 1)))

        sigma_x_given_y = 1 / sp.sqrt(1 / sigma_x**2 + 1 / sigma_y**2)
        mu_x_given_y = sigma_x_given_y**2 * y_observed / sigma_y**2
        expected_posterior_x = st.norm(mu_x_given_y, sigma_x_given_y)
        x = sp.linspace(-8, 8)
        max_distribution_difference = sp.absolute(f_empirical(x) - expected_posterior_x.cdf(x)).max()
        self.assertLess(max_distribution_difference, 0.052)
        self.assertEqual(history.t, nr_populations)
        mean_emp, std_emp = mean_and_std(posterior_x, posterior_weight)
        self.assertLess(abs(mean_emp - mu_x_given_y), .07)
        self.assertLess(abs(std_emp - sigma_x_given_y), .12)

    def test_two_competing_gaussians_single_population(self):
        sigma_x = .5
        sigma_y = .5
        y_observed = 1

        def model(args):
            return {"y": st.norm(args['x'], sigma_y).rvs()}

        models = [model, model]
        model_prior = RV("randint", 0, 2)
        nr_particles = 500
        mu_x_1, mu_x_2 = 0, 1
        parameter_given_model_prior_distribution = [Distribution(x=RV("norm", mu_x_1, sigma_x)),
                                                    Distribution(x=RV("norm", mu_x_2, sigma_x))]
        parameter_perturbation_kernels = [lambda t, stat: Kernel(stat['cov']) for _ in range(2)]
        abc = ABCSMC(models, model_prior, ModelPerturbationKernel(2, probability_to_stay=.7),
                     parameter_given_model_prior_distribution, parameter_perturbation_kernels,
                     PercentileDistanceFunction(measures_to_use=["y"]), MedianEpsilon(.02), nr_particles,
                     max_nr_allowed_sample_attempts_per_particle=2000)

        model_names = ["m1", "m2"]
        options = {'db_path': self.db}
        abc.set_data({"y": y_observed}, 0, {}, options, model_names)

        minimum_epsilon = -1
        nr_populations = 1
        nr_samples_per_particles = [1] * nr_populations
        abc.do_not_stop_when_only_single_model_alive()
        history = abc.run(nr_samples_per_particles, minimum_epsilon)
        p1_emp, p2_emp = history.get_model_probabilities(-1)

        def p_y_given_model(mu_x_model):
            return st.norm(mu_x_model, sp.sqrt(sigma_y**2+sigma_x**2)).pdf(y_observed)

        p1_expected_unnormalized = p_y_given_model(mu_x_1)
        p2_expected_unnormalized = p_y_given_model(mu_x_2)
        p1_expected = p1_expected_unnormalized / (p1_expected_unnormalized + p2_expected_unnormalized)
        p2_expected = p2_expected_unnormalized / (p1_expected_unnormalized + p2_expected_unnormalized)
        self.assertEqual(history.t, nr_populations)
        self.assertLess(abs(p1_emp - p1_expected) + abs(p2_emp - p2_expected), .07)

    def test_two_competing_gaussians_multiple_population(self):
        # Define a gaussian model
        sigma = .5

        def model(args):
            return {"y": st.norm(args['x'], sigma).rvs()}


        # We define two models, but they are identical so far
        models = [model, model]

        # The prior over the model classes is uniform
        model_prior = RV("randint", 0, 2)

        # However, our models' priors are not the same. Their mean differs.
        mu_x_1, mu_x_2 = 0, 1
        parameter_given_model_prior_distribution = [Distribution(x=RV("norm", mu_x_1, sigma)),
                                                    Distribution(x=RV("norm", mu_x_2, sigma))]

        # Particles are perturbed in a Gaussian fashion
        parameter_perturbation_kernels = [lambda t, stat: Kernel(stat['cov']) for _ in range(2)]

        # We plug all the ABC setup together
        nr_particles = 400
        abc = ABCSMC(models, model_prior, ModelPerturbationKernel(2, probability_to_stay=.7),
                     parameter_given_model_prior_distribution, parameter_perturbation_kernels,
                     PercentileDistanceFunction(measures_to_use=["y"]), MedianEpsilon(.2), nr_particles,
                     max_nr_allowed_sample_attempts_per_particle=2000)

        # Finally we add meta data such as model names and define where to store the results
        model_names = ["m1", "m2"]
        options = {'db_path': self.db}
        # y_observed is the important piece here: our actual observation.
        y_observed = 1
        abc.set_data({"y": y_observed}, 0, {}, options, model_names)

        # We run the ABC with 3 populations max
        minimum_epsilon = .05
        nr_populations = 3
        nr_samples_per_particles = [1] * nr_populations
        history = abc.run(nr_samples_per_particles, minimum_epsilon)

        # Evaluate the model probabililties
        p1_emp, p2_emp = history.get_model_probabilities(-1)
        print(p1_emp, p2_emp)

        def p_y_given_model(mu_x_model):
            return st.norm(mu_x_model, sp.sqrt(sigma**2 + sigma**2)).pdf(y_observed)

        p1_expected_unnormalized = p_y_given_model(mu_x_1)
        p2_expected_unnormalized = p_y_given_model(mu_x_2)
        p1_expected = p1_expected_unnormalized / (p1_expected_unnormalized + p2_expected_unnormalized)
        p2_expected = p2_expected_unnormalized / (p1_expected_unnormalized + p2_expected_unnormalized)
        self.assertEqual(history.t, nr_populations)
        self.assertLess(abs(p1_emp - p1_expected) + abs(p2_emp - p2_expected), .07)


if __name__ == "__main__":
    unittest.main()