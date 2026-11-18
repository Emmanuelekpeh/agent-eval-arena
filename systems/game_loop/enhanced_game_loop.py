    def _render_frame(self, delta_time: float):
        if not self.running or not self.screen:
            return

        # Get systems
        vis_integration = self.system_manager.get_system("visualization_integration")
        agent_system = self.system_manager.get_system("agent_system") # Fetch agent system

        # Clear screen
        if vis_integration and hasattr(vis_integration, 'renderer'):
            vis_integration.renderer.clear_screen()
        else:
            self.screen.fill(self.config.colors.get('BLACK', (0, 0, 0))) # Fallback clear

        # --- Primary Rendering via VisualizationIntegration ---
        if vis_integration and hasattr(vis_integration, 'render'):
            try:
                vis_integration.render(delta_time)
                # logger.debug("Called VisualizationIntegration.render")
            except Exception as e:
                logger.exception("Error during VisualizationIntegration.render", exc_info=True)
                self.running = False
                return
        else:
            logger.warning("VisualizationIntegration not available or missing render method. Rendering may be incomplete.")
            # Fallback: Attempt to render environment directly if VisualizationIntegration is missing
            # NO FALLBACK - Rendering is now solely the responsibility of VisualizationIntegration
            # We removed the fallback call: self.environment.render(self.screen)

        # --- UI Rendering (if applicable, e.g., via a UI System) ---
        # Example: ui_system = self.system_manager.get_system("ui_system")
        # if ui_system:
        #     ui_system.render(self.screen)

        # --- Final Screen Update ---
        try:
            pygame.display.flip()
            # logger.debug("pygame.display.flip() called")
        except pygame.error as e:
            logger.error(f"Failed to flip display: {e}")
            self.running = False 