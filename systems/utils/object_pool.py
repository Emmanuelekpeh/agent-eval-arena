import logging
from collections import deque
from typing import Type, Any, Optional, Tuple, Dict

logger = logging.getLogger(__name__)

class ObjectPool:
    """A generic object pool for reusing objects."""

    def __init__(self, cls: Type, initial_size: int = 10, max_size: Optional[int] = None, *init_args: Any, **init_kwargs: Any):
        """
        Initialize the object pool.

        Args:
            cls (Type): The class of objects to pool.
            initial_size (int): The number of objects to create initially.
            max_size (Optional[int]): The maximum number of objects allowed in the pool (both used and unused).
                                      If None, the pool can grow indefinitely.
            *init_args: Positional arguments to pass to the class constructor.
            **init_kwargs: Keyword arguments to pass to the class constructor.
        """
        self._cls = cls
        self._init_args = init_args
        self._init_kwargs = init_kwargs
        self._max_size = max_size
        self._unused = deque()
        self._used_count = 0

        # Pre-populate the pool
        for _ in range(initial_size):
            obj = self._create_new_object()
            if obj:
                self._unused.append(obj)
            else:
                # Stop pre-populating if max size is reached
                break
        logger.info(f"Initialized ObjectPool for {self._cls.__name__} with {len(self._unused)} initial objects.")

    def _create_new_object(self) -> Optional[Any]:
        """Create a new instance of the pooled class."""
        if self._max_size is not None and self.get_total_objects() >= self._max_size:
            logger.warning(f"ObjectPool for {self._cls.__name__} reached max size ({self._max_size}). Cannot create new object.")
            return None
        try:
            return self._cls(*self._init_args, **self._init_kwargs)
        except Exception as e:
            logger.error(f"Failed to create new object of type {self._cls.__name__}: {e}")
            return None

    def get(self, **reset_kwargs: Any) -> Optional[Any]:
        """
        Get an object from the pool. Reuses an unused object if available,
        otherwise creates a new one if under max_size.

        Args:
            **reset_kwargs: Keyword arguments to pass to the object's reset method.

        Returns:
            An initialized object from the pool, or None if the pool is full
            or cannot create new objects.
        """
        obj = None
        if self._unused:
            obj = self._unused.popleft()
            # logger.debug(f"Reusing object {id(obj)} from pool {self._cls.__name__}")
        else:
            obj = self._create_new_object()
            if obj:
                logger.debug(f"Created new object {id(obj)} ({self._cls.__name__}) for pool. Total: {self.get_total_objects()}")
            else:
                return None # Pool is full or creation failed

        # Reset the object before returning
        if hasattr(obj, 'reset'):
            try:
                # Separate core positional args from optional kwargs IF they exist in reset_kwargs
                # This assumes the target class (e.g., Bullet) has specific positional args in reset
                # This is a bit fragile, relies on knowing Bullet's signature.
                core_args = []
                kw_args = {}
                
                # --- Specific Handling for Bullet ---
                if self._cls.__name__ == 'Bullet': # Check if we're pooling Bullets
                     # Extract args that Bullet.reset expects positionally
                     pos_args_keys = ['x', 'y', 'angle', 'color']
                     for key in pos_args_keys:
                          if key in reset_kwargs:
                               core_args.append(reset_kwargs.pop(key)) # Remove from kwargs
                          # else: Maybe raise error or use default if required? For now, assume they are passed.
                     
                     # Remaining kwargs are passed as keywords
                     kw_args = reset_kwargs 
                     obj.reset(*core_args, **kw_args) # Call with positional and keyword args separated
                # --- Fallback for other pooled types ---
                else: 
                    obj.reset(**reset_kwargs) # Original behavior for non-Bullet pools
                # --- End Specific Handling ---

            except TypeError as e:
                 # Add more specific logging for TypeError
                 logger.error(f"TypeError resetting {id(obj)} ({self._cls.__name__}): {e}. Args passed: core={core_args if 'core_args' in locals() else 'N/A'}, kwargs={kw_args if 'kw_args' in locals() else reset_kwargs}")
            except Exception as e:
                logger.error(f"Failed to reset object {id(obj)} of type {self._cls.__name__}: {e}. Args passed: {reset_kwargs}")
        
        self._used_count += 1
        return obj

    def release(self, obj: Any) -> None:
        """
        Release an object back into the pool.

        Args:
            obj (Any): The object to release.
        """
        if not isinstance(obj, self._cls):
            logger.warning(f"Attempted to release object of incorrect type ({type(obj).__name__}) into pool for {self._cls.__name__}.")
            return

        # Safety check: Only prevent adding if it's ALREADY in the unused queue.
        # Removed the check for self.get_total_objects() >= self._max_size
        if obj in self._unused:
            logger.warning(f"Attempted to release object {id(obj)} ({self._cls.__name__}) which is already in the unused queue.")
            # Do not decrement used_count here, as it wasn't truly 'used' if already in _unused
        else:
             # Always add back to unused if it's a valid object and not already there.
            self._unused.append(obj)
            logger.debug(f"Released object {id(obj)} ({self._cls.__name__}) back to pool. Unused: {self.get_unused_count()}, Used: {self._used_count - 1}")

            # Decrement used count safely only after successful release
            if self._used_count > 0:
                self._used_count -= 1
            else:
                # This case should ideally not happen if logic is correct
                logger.warning(f"Released object {id(obj)} but used count was already zero for pool {self._cls.__name__}.")

    def get_used_count(self) -> int:
        """Return the number of objects currently checked out."""
        return self._used_count

    def get_unused_count(self) -> int:
        """Return the number of objects available in the pool."""
        return len(self._unused)

    def get_total_objects(self) -> int:
        """Return the total number of objects managed by the pool (used + unused)."""
        return self.get_used_count() + self.get_unused_count()

    def get_max_size(self) -> Optional[int]:
        """Return the maximum allowed size of the pool."""
        return self._max_size 