"""
Genetic Algorithm implementation for AI agent evolution.

This module provides a comprehensive genetic algorithm implementation 
for evolving neural network weights and agent parameters.
"""

import numpy as np
import random
from typing import List, Dict, Any, Tuple, Callable, Optional, Union

class GeneticAlgorithm:
    """
    Genetic algorithm implementation for evolving agent neural networks and parameters.
    
    This implementation supports various selection, crossover, and mutation methods
    with configurable parameters for fine-tuning the evolution process.
    """
    
    def __init__(self, 
                population_size: int = 50,
                mutation_rate: float = 0.2,
                crossover_rate: float = 0.7,
                elite_size: int = 5,
                tournament_size: int = 3,
                adaptation_rate: float = 0.05):
        """
        Initialize the genetic algorithm.
        
        Args:
            population_size: Size of the population to maintain
            mutation_rate: Probability of mutation for each gene
            crossover_rate: Probability of crossover between parents
            elite_size: Number of top individuals to preserve unchanged
            tournament_size: Size of tournament for selection
            adaptation_rate: Rate at which mutation parameters adapt
        """
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elite_size = elite_size
        self.tournament_size = tournament_size
        self.adaptation_rate = adaptation_rate
        
        # Additional parameters for adaptive mutation
        self.min_mutation = 0.01
        self.max_mutation = 0.5
        self.mutation_strength = 0.1  # Standard deviation for Gaussian mutation
        
        # Performance tracking
        self.generation = 0
        self.best_fitness_history = []
        self.avg_fitness_history = []
        
    def select_parents(self, 
                     population: List[Any], 
                     fitness_scores: List[float],
                     selection_method: str = 'tournament') -> List[Any]:
        """
        Select parents for reproduction using the specified method.
        
        Args:
            population: List of individuals (agents or weight sets)
            fitness_scores: List of fitness scores for each individual
            selection_method: Method to use for selection ('tournament', 'roulette', or 'rank')
            
        Returns:
            List of selected parents
        """
        if selection_method == 'tournament':
            return self._tournament_selection(population, fitness_scores)
        elif selection_method == 'roulette':
            return self._roulette_selection(population, fitness_scores)
        elif selection_method == 'rank':
            return self._rank_selection(population, fitness_scores)
        else:
            # Default to tournament selection
            return self._tournament_selection(population, fitness_scores)
    
    def _tournament_selection(self, 
                           population: List[Any], 
                           fitness_scores: List[float]) -> List[Any]:
        """
        Select parents using tournament selection.
        
        Args:
            population: List of individuals
            fitness_scores: List of fitness scores
            
        Returns:
            List of selected parents
        """
        selected_parents = []
        
        # Create array of indices and corresponding fitness scores
        indices = np.arange(len(population))
        
        # Select population_size parents
        for _ in range(self.population_size):
            # Randomly select tournament_size individuals
            tournament_indices = np.random.choice(indices, size=self.tournament_size, replace=False)
            tournament_fitness = [fitness_scores[i] for i in tournament_indices]
            
            # Select the winner (highest fitness)
            winner_idx = tournament_indices[np.argmax(tournament_fitness)]
            selected_parents.append(population[winner_idx])
            
        return selected_parents
    
    def _roulette_selection(self, 
                         population: List[Any], 
                         fitness_scores: List[float]) -> List[Any]:
        """
        Select parents using roulette wheel selection.
        
        Args:
            population: List of individuals
            fitness_scores: List of fitness scores
            
        Returns:
            List of selected parents
        """
        selected_parents = []
        
        # Handle negative fitness scores by shifting all scores to be positive
        min_fitness = min(fitness_scores)
        if min_fitness < 0:
            adjusted_fitness = [score - min_fitness + 0.1 for score in fitness_scores]
        else:
            adjusted_fitness = fitness_scores.copy()
        
        # Calculate selection probabilities
        total_fitness = sum(adjusted_fitness)
        if total_fitness == 0:
            # If all fitness scores are 0, select randomly
            return random.choices(population, k=self.population_size)
            
        probabilities = [score / total_fitness for score in adjusted_fitness]
        
        # Select population_size parents using roulette wheel
        selected_parents = random.choices(
            population, 
            weights=probabilities, 
            k=self.population_size
        )
        
        return selected_parents
    
    def _rank_selection(self, 
                     population: List[Any], 
                     fitness_scores: List[float]) -> List[Any]:
        """
        Select parents using rank-based selection.
        
        Args:
            population: List of individuals
            fitness_scores: List of fitness scores
            
        Returns:
            List of selected parents
        """
        selected_parents = []
        
        # Create array of indices and sort by fitness
        indices = np.argsort(fitness_scores)[::-1]  # Descending order
        
        # Assign ranks (higher fitness = higher rank)
        ranks = np.arange(len(population), 0, -1)
        
        # Calculate selection probabilities based on rank
        total_rank = sum(ranks)
        probabilities = [rank / total_rank for rank in ranks]
        
        # Select population_size parents using rank probabilities
        ranked_population = [population[i] for i in indices]
        selected_parents = random.choices(
            ranked_population, 
            weights=probabilities, 
            k=self.population_size
        )
        
        return selected_parents
        
    def crossover(self, 
                parent1: Union[np.ndarray, Dict[str, np.ndarray]],
                parent2: Union[np.ndarray, Dict[str, np.ndarray]],
                crossover_method: str = 'uniform') -> Tuple[Any, Any]:
        """
        Perform crossover between two parents.
        
        Args:
            parent1: First parent (numpy array or dict of arrays)
            parent2: Second parent (numpy array or dict of arrays)
            crossover_method: Method to use for crossover ('uniform', 'single_point', or 'two_point')
            
        Returns:
            Tuple of (child1, child2)
        """
        # Check if crossover should occur based on crossover rate
        if random.random() > self.crossover_rate:
            return parent1, parent2
            
        # Handle dictionary-based weights (like in MLPAgent)
        if isinstance(parent1, dict) and isinstance(parent2, dict):
            child1 = {}
            child2 = {}
            
            for key in parent1.keys():
                if key in parent2:
                    child1[key], child2[key] = self._crossover_arrays(
                        parent1[key], parent2[key], crossover_method
                    )
                else:
                    child1[key] = parent1[key].copy()
                    child2[key] = parent1[key].copy()
                    
            return child1, child2
        
        # Handle numpy arrays
        elif isinstance(parent1, np.ndarray) and isinstance(parent2, np.ndarray):
            return self._crossover_arrays(parent1, parent2, crossover_method)
        
        # If types don't match or aren't supported, return originals
        return parent1, parent2
    
    def _crossover_arrays(self, 
                       array1: np.ndarray, 
                       array2: np.ndarray,
                       method: str = 'uniform') -> Tuple[np.ndarray, np.ndarray]:
        """
        Perform crossover between two arrays.
        
        Args:
            array1: First parent array
            array2: Second parent array
            method: Crossover method
            
        Returns:
            Tuple of (child1_array, child2_array)
        """
        # Ensure arrays have the same shape
        if array1.shape != array2.shape:
            # Return copies if shapes don't match
            return array1.copy(), array2.copy()
            
        if method == 'uniform':
            # Uniform crossover
            mask = np.random.random(array1.shape) < 0.5
            child1 = np.where(mask, array1, array2)
            child2 = np.where(mask, array2, array1)
            
        elif method == 'single_point':
            # Single-point crossover
            child1 = array1.copy()
            child2 = array2.copy()
            
            # Flatten arrays for easier crossover
            flat1 = child1.flatten()
            flat2 = child2.flatten()
            
            # Choose crossover point
            point = random.randint(1, len(flat1) - 1)
            
            # Swap segments
            flat1[point:], flat2[point:] = flat2[point:].copy(), flat1[point:].copy()
            
            # Reshape back to original shape
            child1 = flat1.reshape(array1.shape)
            child2 = flat2.reshape(array2.shape)
            
        elif method == 'two_point':
            # Two-point crossover
            child1 = array1.copy()
            child2 = array2.copy()
            
            # Flatten arrays for easier crossover
            flat1 = child1.flatten()
            flat2 = child2.flatten()
            
            # Choose crossover points
            length = len(flat1)
            point1 = random.randint(1, length // 3)
            point2 = random.randint(2 * length // 3, length - 1)
            
            # Swap middle segment
            flat1[point1:point2], flat2[point1:point2] = flat2[point1:point2].copy(), flat1[point1:point2].copy()
            
            # Reshape back to original shape
            child1 = flat1.reshape(array1.shape)
            child2 = flat2.reshape(array2.shape)
            
        else:
            # Default to uniform crossover
            mask = np.random.random(array1.shape) < 0.5
            child1 = np.where(mask, array1, array2)
            child2 = np.where(mask, array2, array1)
            
        return child1, child2
    
    def mutate(self, 
             individual: Union[np.ndarray, Dict[str, np.ndarray]],
             mutation_method: str = 'gaussian') -> Any:
        """
        Mutate an individual.
        
        Args:
            individual: Individual to mutate (numpy array or dict of arrays)
            mutation_method: Method to use for mutation ('gaussian', 'uniform', or 'swap')
            
        Returns:
            Mutated individual
        """
        # Handle dictionary-based weights (like in MLPAgent)
        if isinstance(individual, dict):
            mutated = {}
            for key, value in individual.items():
                mutated[key] = self._mutate_array(value, mutation_method)
            return mutated
            
        # Handle numpy arrays
        elif isinstance(individual, np.ndarray):
            return self._mutate_array(individual, mutation_method)
            
        # If type isn't supported, return original
        return individual
    
    def _mutate_array(self, 
                   array: np.ndarray, 
                   method: str = 'gaussian') -> np.ndarray:
        """
        Mutate a numpy array.
        
        Args:
            array: Array to mutate
            method: Mutation method
            
        Returns:
            Mutated array
        """
        mutated = array.copy()
        
        # Create mutation mask
        mutation_mask = np.random.random(array.shape) < self.mutation_rate
        
        if method == 'gaussian':
            # Gaussian mutation
            mutations = np.random.normal(0, self.mutation_strength, size=array.shape)
            mutated[mutation_mask] += mutations[mutation_mask]
            
        elif method == 'uniform':
            # Uniform mutation
            mutations = np.random.uniform(-0.5, 0.5, size=array.shape)
            mutated[mutation_mask] += mutations[mutation_mask]
            
        elif method == 'swap':
            # Swap mutation (only for 1D arrays)
            if array.ndim == 1 and np.sum(mutation_mask) >= 2:
                swap_indices = np.where(mutation_mask)[0]
                if len(swap_indices) >= 2:
                    for _ in range(len(swap_indices) // 2):
                        i, j = np.random.choice(swap_indices, size=2, replace=False)
                        mutated[i], mutated[j] = mutated[j], mutated[i]
                        
        else:
            # Default to gaussian mutation
            mutations = np.random.normal(0, self.mutation_strength, size=array.shape)
            mutated[mutation_mask] += mutations[mutation_mask]
            
        return mutated
    
    def evolve(self, 
             population: List[Any], 
             fitness_scores: List[float],
             selection_method: str = 'tournament',
             crossover_method: str = 'uniform',
             mutation_method: str = 'gaussian') -> List[Any]:
        """
        Evolve a population using genetic operators.
        
        Args:
            population: List of individuals
            fitness_scores: List of fitness scores
            selection_method: Method to use for selection
            crossover_method: Method to use for crossover
            mutation_method: Method to use for mutation
            
        Returns:
            New evolved population
        """
        # Track fitness statistics
        best_fitness = max(fitness_scores)
        avg_fitness = sum(fitness_scores) / len(fitness_scores)
        self.best_fitness_history.append(best_fitness)
        self.avg_fitness_history.append(avg_fitness)
        
        # Sort population by fitness
        sorted_indices = np.argsort(fitness_scores)[::-1]  # Descending order
        sorted_population = [population[i] for i in sorted_indices]
        
        # Preserve elites
        elites = sorted_population[:self.elite_size]
        
        # Select parents
        parents = self.select_parents(population, fitness_scores, selection_method)
        
        # Create new population through crossover and mutation
        new_population = []
        
        # Add elites to new population
        new_population.extend(elites)
        
        # Fill the rest of the population with offspring
        while len(new_population) < self.population_size:
            # Select two parents
            parent1 = random.choice(parents)
            parent2 = random.choice(parents)
            
            # Perform crossover
            child1, child2 = self.crossover(parent1, parent2, crossover_method)
            
            # Perform mutation
            child1 = self.mutate(child1, mutation_method)
            child2 = self.mutate(child2, mutation_method)
            
            # Add to new population
            new_population.append(child1)
            if len(new_population) < self.population_size:
                new_population.append(child2)
        
        # Adapt mutation parameters based on fitness improvement
        self._adapt_mutation_parameters()
        
        # Increment generation counter
        self.generation += 1
        
        return new_population
    
    def _adapt_mutation_parameters(self) -> None:
        """Adapt mutation parameters based on evolution progress."""
        # Only adapt if we have at least 2 generations of data
        if len(self.best_fitness_history) < 2:
            return
            
        # Check if fitness is improving
        improvement = self.best_fitness_history[-1] - self.best_fitness_history[-2]
        
        if improvement > 0:
            # If improving, gradually reduce mutation to fine-tune
            self.mutation_rate = max(
                self.min_mutation,
                self.mutation_rate * (1 - self.adaptation_rate)
            )
            self.mutation_strength *= 0.95
        else:
            # If stuck, increase mutation to explore more
            self.mutation_rate = min(
                self.max_mutation,
                self.mutation_rate * (1 + self.adaptation_rate)
            )
            self.mutation_strength *= 1.05
    
    def get_evolution_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the evolution process.
        
        Returns:
            Dictionary of evolution statistics
        """
        return {
            'generation': self.generation,
            'best_fitness_history': self.best_fitness_history,
            'avg_fitness_history': self.avg_fitness_history,
            'current_mutation_rate': self.mutation_rate,
            'current_mutation_strength': self.mutation_strength
        } 