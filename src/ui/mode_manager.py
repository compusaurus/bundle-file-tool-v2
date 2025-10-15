# ============================================================================
# SOURCEFILE: mode_manager.py
# RELPATH: bundle_file_tool_v2/src/ui/mode_manager.py
# PROJECT: Bundle File Tool v2.1
# TEAM: Ringo (Owner), John (Lead Dev), George (Architect), Paul (Lead Analyst)
# VERSION: 2.1.0
# LIFECYCLE: Proposed
# STATUS: NEW - Phase 4 implementation per George's architectural guidance
# DESCRIPTION: Central state manager for application mode with observer pattern
# ============================================================================

"""
Mode Manager for Bundle File Tool v2.1.

Implements observer pattern for managing application state (Un-bundle vs Bundle mode)
and notifying UI components of mode changes. This is the "central nervous system" of
the dual-mode UI architecture.
"""

from enum import Enum, auto
from typing import Callable, List


class AppMode(Enum):
    """
    Application operating modes.
    
    UNBUNDLE: Parse bundle files and extract to directory structure
    BUNDLE: Create bundle files from directory structure
    """
    UNBUNDLE = auto()
    BUNDLE = auto()


class ModeManager:
    """
    Central state manager for application mode with observer pattern.
    
    This class manages the application's current mode and notifies all registered
    listeners when the mode changes. UI components subscribe to mode changes and
    update themselves accordingly.
    
    Architecture:
    - Single source of truth for application mode
    - Observer pattern for loose coupling between components
    - Mode changes trigger cascading UI updates
    
    Example:
        >>> manager = ModeManager()
        >>> def on_mode_change(new_mode):
        ...     print(f"Mode changed to: {new_mode.name}")
        >>> manager.add_listener(on_mode_change)
        >>> manager.set_mode(AppMode.BUNDLE)
        Mode changed to: BUNDLE
    """
    
    def __init__(self, initial_mode: AppMode = AppMode.UNBUNDLE):
        """
        Initialize mode manager.
        
        Args:
            initial_mode: Starting mode for application (default: UNBUNDLE)
        """
        self._mode: AppMode = initial_mode
        self._listeners: List[Callable[[AppMode], None]] = []
    
    def add_listener(self, listener_func: Callable[[AppMode], None]) -> None:
        """
        Register a callback function to be notified of mode changes.
        
        The listener function will be called immediately with the current mode
        upon registration, then called again whenever the mode changes.
        
        Args:
            listener_func: Callback function that accepts an AppMode parameter
            
        Example:
            >>> def ui_update(mode):
            ...     print(f"UI updating for {mode.name} mode")
            >>> manager.add_listener(ui_update)
            UI updating for UNBUNDLE mode
        """
        if listener_func not in self._listeners:
            self._listeners.append(listener_func)
            # Call immediately with current mode so listener can initialize
            listener_func(self._mode)
    
    def remove_listener(self, listener_func: Callable[[AppMode], None]) -> bool:
        """
        Unregister a callback function.
        
        Args:
            listener_func: The callback function to remove
            
        Returns:
            True if listener was removed, False if not found
        """
        if listener_func in self._listeners:
            self._listeners.remove(listener_func)
            return True
        return False
    
    def set_mode(self, new_mode: AppMode) -> None:
        """
        Change the application mode and notify all listeners.
        
        If the new mode is the same as the current mode, no notifications
        are sent (optimization to prevent unnecessary UI updates).
        
        Args:
            new_mode: The mode to switch to
            
        Example:
            >>> manager.set_mode(AppMode.BUNDLE)
            # All registered listeners are notified
        """
        if new_mode != self._mode:
            self._mode = new_mode
            self._notify_listeners()
    
    def get_mode(self) -> AppMode:
        """
        Get the current application mode.
        
        Returns:
            Current AppMode value
        """
        return self._mode
    
    def is_unbundle_mode(self) -> bool:
        """
        Check if currently in un-bundle mode.
        
        Returns:
            True if in UNBUNDLE mode
        """
        return self._mode == AppMode.UNBUNDLE
    
    def is_bundle_mode(self) -> bool:
        """
        Check if currently in bundle mode.
        
        Returns:
            True if in BUNDLE mode
        """
        return self._mode == AppMode.BUNDLE
    
    def toggle_mode(self) -> AppMode:
        """
        Toggle between UNBUNDLE and BUNDLE modes.
        
        Returns:
            The new mode after toggling
        """
        if self._mode == AppMode.UNBUNDLE:
            self.set_mode(AppMode.BUNDLE)
        else:
            self.set_mode(AppMode.UNBUNDLE)
        return self._mode
    
    def _notify_listeners(self) -> None:
        """
        Call all registered listener functions with the current mode.
        
        This is an internal method called automatically by set_mode().
        Listeners are notified in the order they were registered.
        """
        for listener in self._listeners:
            try:
                listener(self._mode)
            except Exception as e:
                # Log error but don't let one bad listener crash the notification chain
                print(f"Error in mode change listener: {e}")
    
    def get_listener_count(self) -> int:
        """
        Get the number of registered listeners (useful for debugging).
        
        Returns:
            Count of registered listeners
        """
        return len(self._listeners)
    
    def clear_listeners(self) -> None:
        """
        Remove all registered listeners (useful for testing/cleanup).
        """
        self._listeners.clear()


# ============================================================================
# LIFECYCLE STATUS: Proposed
# ARCHITECTURE: Observer pattern per George's Phase 4 guidance
# DEPENDENCIES: None (standalone state manager)
# TESTS: Unit tests for observer pattern, mode switching, listener management
# UI INTEGRATION: Main window subscribes to mode changes for UI updates
# NEXT STEPS: Integrate with main_window.py for dual-mode UI
# ============================================================================
