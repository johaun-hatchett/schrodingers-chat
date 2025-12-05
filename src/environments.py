"""Defines the environment of the game with extensible physics problem support."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

import random
import math


class ProblemType(Enum):
    """Enumeration of supported physics problem types."""
    BLOCK_ON_INCLINE = "block_on_incline"
    PENDULUM = "pendulum"
    PROJECTILE_MOTION = "projectile_motion"
    ROCKET_EQUATION = "rocket_equation"


class BaseEnvironment(ABC):
    """Abstract base class for physics problem environments."""
    
    def __init__(self):
        """Initialize the environment with physically consistent random values."""
        self._initialize_parameters()
    
    @abstractmethod
    def _initialize_parameters(self) -> None:
        """Generate and set physically consistent random parameters for the problem."""
        pass
    
    @abstractmethod
    def get_problem_description(self) -> str:
        """Return a description of the physics problem."""
        pass
    
    @abstractmethod
    def get_available_probes(self) -> Dict[str, bool]:
        """Return a dictionary of available measurement tools/probes and their availability."""
        pass
    
    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Return a dictionary of all environment parameters."""
        pass
    
    @abstractmethod
    def validate_answer(self, answer: Any) -> Tuple[bool, str]:
        """
        Validate a student's answer.
        
        Returns:
            tuple: (is_correct: bool, feedback: str)
        """
        pass
    
    def get(self, key: str) -> Any:
        """Get a specific parameter by key."""
        return self.__dict__.get(key)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert environment to dictionary representation."""
        return self.get_parameters()


class BlockOnInclineEnvironment(BaseEnvironment):
    """Environment for block-on-incline friction problem."""
    
    def _initialize_parameters(self) -> None:
        """Generate physically consistent parameters for block-on-incline problem."""
        # Mass between 2 kg and 20 kg (integers)
        self.mass = random.randint(2, 20)
        
        # Select a static friction coefficient realistically between 0.2 and 0.8
        self.coeff_static_friction = round(random.uniform(0.2, 0.8), 2)
        
        # Select gravity constant
        self.gravity = 9.81  # Earth's gravity, keep constant for now
        
        # Compute critical angle theta = arctan(mu_s)
        theta_critical_deg = math.degrees(math.atan(self.coeff_static_friction))
        
        # Generate a plausible incline angle: sometimes subcritical, sometimes critical, 
        # sometimes slightly supercritical
        offset = random.choice([
            -random.uniform(0, 5),   # a bit less than critical
            0,                       # exactly critical
            random.uniform(0.1, 5),  # a bit greater than critical
        ])
        self.incline_angle = round(theta_critical_deg + offset, 1)
        # Bound angle between 5 and 50 degrees for realism
        self.incline_angle = max(5, min(self.incline_angle, 50))
    
    def get_problem_description(self) -> str:
        return (
            "You are in a physics lab. In front of you is a wooden block and a "
            "wooden inclined plane. Your goal is to determine the coefficient of static "
            "friction between the block and the plane. You have a mass scale and an "
            "inclinometer at your disposal."
        )
    
    def get_available_probes(self) -> Dict[str, bool]:
        return {
            "mass_scale": True,
            "inclinometer": True
        }
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "mass": self.mass,
            "incline_angle": self.incline_angle,
            "coeff_static_friction": self.coeff_static_friction,
            "gravity": self.gravity,
        }
    
    def validate_answer(self, answer: Any) -> Tuple[bool, str]:
        """Validate the coefficient of static friction answer."""
        try:
            answer_value = float(answer)
            correct_value = self.coeff_static_friction
            tolerance = 0.01
            
            if abs(answer_value - correct_value) < tolerance:
                return True, f"Correct! The coefficient of static friction is {correct_value}."
            else:
                return False, f"Incorrect. The correct coefficient is {correct_value}."
        except (ValueError, TypeError):
            return False, "Invalid answer format. Please provide a numeric value."


class PendulumEnvironment(BaseEnvironment):
    """Environment for simple pendulum problem."""
    
    def _initialize_parameters(self) -> None:
        """Generate physically consistent parameters for pendulum problem."""
        # Length between 0.5 m and 2.0 m
        self.length = round(random.uniform(0.5, 2.0), 2)
        
        # Mass between 0.1 kg and 2.0 kg
        self.mass = round(random.uniform(0.1, 2.0), 2)
        
        # Initial angle (amplitude) between 5 and 30 degrees
        self.initial_angle = round(random.uniform(5, 30), 1)
        
        # Gravity constant
        self.gravity = 9.81
        
        # Calculate period: T = 2π√(L/g)
        self.period = 2 * math.pi * math.sqrt(self.length / self.gravity)
    
    def get_problem_description(self) -> str:
        return (
            "You are in a physics lab with a simple pendulum setup. Your goal is to determine "
            "the period of oscillation or the gravitational acceleration. You have a stopwatch, "
            "a ruler, and a protractor at your disposal."
        )
    
    def get_available_probes(self) -> Dict[str, bool]:
        return {
            "stopwatch": True,
            "ruler": True,
            "protractor": True,
            "motion_sensor": False  # Starts as unavailable
        }
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "length": self.length,
            "mass": self.mass,
            "initial_angle": self.initial_angle,
            "gravity": self.gravity,
            "period": round(self.period, 3),
        }
    
    def validate_answer(self, answer: Any) -> Tuple[bool, str]:
        """Validate the period or gravity answer."""
        try:
            answer_value = float(answer)
            # Check if answer matches period (within 5% tolerance)
            period_tolerance = self.period * 0.05
            if abs(answer_value - self.period) < period_tolerance:
                return True, f"Correct! The period is {self.period:.3f} s."
            else:
                return False, f"Incorrect. The correct period is {self.period:.3f} s."
        except (ValueError, TypeError):
            return False, "Invalid answer format. Please provide a numeric value."


class ProjectileMotionEnvironment(BaseEnvironment):
    """Environment for projectile motion problem."""
    
    def _initialize_parameters(self) -> None:
        """Generate physically consistent parameters for projectile motion problem."""
        # Initial velocity between 10 m/s and 50 m/s
        self.initial_velocity = round(random.uniform(10, 50), 1)
        
        # Launch angle between 15 and 75 degrees
        self.launch_angle = round(random.uniform(15, 75), 1)
        
        # Initial height (optional, can be 0 for ground launch)
        self.initial_height = round(random.choice([0, random.uniform(1, 10)]), 1)
        
        # Gravity constant
        self.gravity = 9.81
        
        # Calculate range, max height, and time of flight
        angle_rad = math.radians(self.launch_angle)
        v0_x = self.initial_velocity * math.cos(angle_rad)
        v0_y = self.initial_velocity * math.sin(angle_rad)
        
        # Time of flight (accounting for initial height)
        if self.initial_height > 0:
            time_of_flight = (v0_y + math.sqrt(v0_y**2 + 2 * self.gravity * self.initial_height)) / self.gravity
        else:
            time_of_flight = 2 * v0_y / self.gravity
        
        self.range = v0_x * time_of_flight
        self.max_height = self.initial_height + (v0_y**2) / (2 * self.gravity)
        self.time_of_flight = time_of_flight
    
    def get_problem_description(self) -> str:
        return (
            "You are in a physics lab with a projectile launcher. Your goal is to determine "
            "the range, maximum height, or time of flight of the projectile. You have a "
            "protractor, a measuring tape, and a motion sensor at your disposal."
        )
    
    def get_available_probes(self) -> Dict[str, bool]:
        return {
            "protractor": True,
            "measuring_tape": True,
            "motion_sensor": True,
            "speedometer": False  # Starts as unavailable
        }
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "initial_velocity": self.initial_velocity,
            "launch_angle": self.launch_angle,
            "initial_height": self.initial_height,
            "gravity": self.gravity,
            "range": round(self.range, 2),
            "max_height": round(self.max_height, 2),
            "time_of_flight": round(self.time_of_flight, 2),
        }
    
    def validate_answer(self, answer: Any) -> Tuple[bool, str]:
        """Validate the range, max height, or time of flight answer."""
        try:
            answer_value = float(answer)
            tolerance = 0.1
            
            # Check against range (most common answer)
            if abs(answer_value - self.range) < tolerance:
                return True, f"Correct! The range is {self.range:.2f} m."
            elif abs(answer_value - self.max_height) < tolerance:
                return True, f"Correct! The maximum height is {self.max_height:.2f} m."
            elif abs(answer_value - self.time_of_flight) < tolerance:
                return True, f"Correct! The time of flight is {self.time_of_flight:.2f} s."
            else:
                return False, (
                    f"Incorrect. Expected values: range={self.range:.2f} m, "
                    f"max_height={self.max_height:.2f} m, "
                    f"time_of_flight={self.time_of_flight:.2f} s."
                )
        except (ValueError, TypeError):
            return False, "Invalid answer format. Please provide a numeric value."


class RocketEquationEnvironment(BaseEnvironment):
    """Environment for rocket equation problem (Tsiolkovsky rocket equation)."""
    
    def _initialize_parameters(self) -> None:
        """Generate physically consistent parameters for rocket problem."""
        # Initial mass (rocket + fuel) between 1000 kg and 10000 kg
        self.initial_mass = random.randint(1000, 10000)
        
        # Final mass (rocket after fuel is expended) between 200 kg and 2000 kg
        self.final_mass = random.randint(200, min(2000, self.initial_mass // 2))
        
        # Exhaust velocity (typical for chemical rockets: 2000-4500 m/s)
        self.exhaust_velocity = round(random.uniform(2000, 4500), 0)
        
        # Calculate delta-v using Tsiolkovsky rocket equation: Δv = v_e * ln(m0/mf)
        self.delta_v = self.exhaust_velocity * math.log(self.initial_mass / self.final_mass)
        
        # Fuel mass
        self.fuel_mass = self.initial_mass - self.final_mass
    
    def get_problem_description(self) -> str:
        return (
            "You are working on a rocket design problem. Your goal is to determine the "
            "delta-v (change in velocity) that can be achieved given the rocket's mass "
            "characteristics. You have access to mass measurements and exhaust velocity data."
        )
    
    def get_available_probes(self) -> Dict[str, bool]:
        return {
            "mass_scale": True,
            "thrust_measuring_device": True,
            "velocity_sensor": False  # Starts as unavailable
        }
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            "initial_mass": self.initial_mass,
            "final_mass": self.final_mass,
            "fuel_mass": self.fuel_mass,
            "exhaust_velocity": self.exhaust_velocity,
            "delta_v": round(self.delta_v, 2),
        }
    
    def validate_answer(self, answer: Any) -> Tuple[bool, str]:
        """Validate the delta-v answer."""
        try:
            answer_value = float(answer)
            tolerance = self.delta_v * 0.02  # 2% tolerance
            
            if abs(answer_value - self.delta_v) < tolerance:
                return True, f"Correct! The delta-v is {self.delta_v:.2f} m/s."
            else:
                return False, f"Incorrect. The correct delta-v is {self.delta_v:.2f} m/s."
        except (ValueError, TypeError):
            return False, "Invalid answer format. Please provide a numeric value."


class EnvironmentFactory:
    """Factory for creating physics problem environments."""
    
    _registry: Dict[ProblemType, type[BaseEnvironment]] = {
        ProblemType.BLOCK_ON_INCLINE: BlockOnInclineEnvironment,
        ProblemType.PENDULUM: PendulumEnvironment,
        ProblemType.PROJECTILE_MOTION: ProjectileMotionEnvironment,
        ProblemType.ROCKET_EQUATION: RocketEquationEnvironment,
    }
    
    @classmethod
    def create(cls, problem_type: ProblemType) -> BaseEnvironment:
        """
        Create an environment instance for the specified problem type.
        
        Args:
            problem_type: The type of physics problem
            
        Returns:
            An instance of the appropriate environment class
            
        Raises:
            ValueError: If the problem type is not supported
        """
        if problem_type not in cls._registry:
            raise ValueError(f"Unsupported problem type: {problem_type}")
        
        return cls._registry[problem_type]()
    
    @classmethod
    def create_from_string(cls, problem_type_str: str) -> BaseEnvironment:
        """
        Create an environment instance from a string representation.
        
        Args:
            problem_type_str: String representation of the problem type
            
        Returns:
            An instance of the appropriate environment class
        """
        try:
            problem_type = ProblemType(problem_type_str)
            return cls.create(problem_type)
        except ValueError:
            raise ValueError(f"Unknown problem type string: {problem_type_str}")
    
    @classmethod
    def register(cls, problem_type: ProblemType, environment_class: type[BaseEnvironment]) -> None:
        """
        Register a new environment class for a problem type.
        
        Args:
            problem_type: The problem type enum
            environment_class: The environment class to register
        """
        cls._registry[problem_type] = environment_class
    
    @classmethod
    def list_available_types(cls) -> List[str]:
        """Return a list of available problem type strings."""
        return [pt.value for pt in cls._registry.keys()]


# Backward compatibility: Export the original class name
Environment = BlockOnInclineEnvironment