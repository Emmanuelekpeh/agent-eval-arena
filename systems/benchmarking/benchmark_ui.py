import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import threading
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from systems.benchmarking.benchmark_runner import BenchmarkRunner
from systems.benchmarking.benchmark_scenarios import BenchmarkScenarioLibrary
from systems.agents.agent_factory import create_agent, get_available_agent_types

class BenchmarkUI:
    """
    A simple UI for running agent benchmarks and visualizing results.
    """
    
    def __init__(self, root):
        self.root = root
        self.root.title("Agent Benchmark Tool")
        self.root.geometry("1000x700")
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Initialize benchmark components
        self.runner = BenchmarkRunner()
        self.scenario_library = BenchmarkScenarioLibrary()
        
        # Get available agent types and scenarios
        self.agent_types = list(get_available_agent_types().keys())
        self.scenarios = self.scenario_library.get_all_scenarios()
        
        # Track active benchmarks and results
        self.active_benchmark = False
        self.benchmark_thread = None
        self.results = {}
        
        # Create UI components
        self._create_menu()
        self._create_main_frame()
        
        # Set up initial state
        self._populate_agent_list()
        self._populate_scenario_list()
    
    def _create_menu(self):
        """Create the application menu."""
        menubar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Save Results", command=self._save_results)
        file_menu.add_command(label="Load Results", command=self._load_results)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Reports menu
        reports_menu = tk.Menu(menubar, tearoff=0)
        reports_menu.add_command(label="Generate Summary Report", command=self._generate_report)
        reports_menu.add_command(label="Generate Performance Graphs", command=self._generate_graphs)
        menubar.add_cascade(label="Reports", menu=reports_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.root.config(menu=menubar)
    
    def _create_main_frame(self):
        """Create the main application frame and components."""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create horizontal split panes
        main_paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Configuration
        left_frame = ttk.Frame(main_paned, padding="5")
        main_paned.add(left_frame, weight=30)
        
        # Right panel - Results
        right_frame = ttk.Frame(main_paned, padding="5")
        main_paned.add(right_frame, weight=70)
        
        # Set up the configuration panel
        self._create_config_panel(left_frame)
        
        # Set up the results panel
        self._create_results_panel(right_frame)
    
    def _create_config_panel(self, parent):
        """Create the configuration panel."""
        # Title
        ttk.Label(parent, text="Benchmark Configuration", font=("Arial", 12, "bold")).pack(pady=(0, 10))
        
        # Agent selection
        agent_frame = ttk.LabelFrame(parent, text="Select Agents", padding="5")
        agent_frame.pack(fill=tk.X, pady=5)
        
        self.agent_listbox = tk.Listbox(agent_frame, selectmode=tk.MULTIPLE, height=6)
        self.agent_listbox.pack(fill=tk.X, expand=True)
        
        # Scenario selection
        scenario_frame = ttk.LabelFrame(parent, text="Select Scenarios", padding="5")
        scenario_frame.pack(fill=tk.X, pady=5)
        
        self.scenario_listbox = tk.Listbox(scenario_frame, selectmode=tk.MULTIPLE, height=8)
        self.scenario_listbox.pack(fill=tk.X, expand=True)
        
        # Benchmark buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Run Single Benchmark", 
                 command=self._run_single_benchmark).pack(fill=tk.X, pady=2)
        ttk.Button(button_frame, text="Run Batch Benchmark", 
                 command=self._run_batch_benchmark).pack(fill=tk.X, pady=2)
        ttk.Button(button_frame, text="Run Agent Comparison", 
                 command=self._run_agent_comparison).pack(fill=tk.X, pady=2)
        
        # Progression benchmark
        prog_frame = ttk.LabelFrame(parent, text="Progression Benchmark", padding="5")
        prog_frame.pack(fill=tk.X, pady=5)
        
        focus_frame = ttk.Frame(prog_frame)
        focus_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(focus_frame, text="Focus Area:").pack(side=tk.LEFT)
        
        self.focus_var = tk.StringVar(value="balanced")
        focus_combo = ttk.Combobox(focus_frame, textvariable=self.focus_var, 
                                 values=["balanced", "combat", "survival", "resource", "team"])
        focus_combo.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        ttk.Button(prog_frame, text="Run Progression Benchmark", 
                 command=self._run_progression_benchmark).pack(fill=tk.X, pady=5)
        
        # Status bar
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        
        ttk.Label(status_frame, text="Status:").pack(side=tk.LEFT)
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT, padx=5)
        
        # Progress bar
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress = ttk.Progressbar(parent, variable=self.progress_var, mode="determinate")
        self.progress.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
    
    def _create_results_panel(self, parent):
        """Create the results panel."""
        # Title
        ttk.Label(parent, text="Benchmark Results", font=("Arial", 12, "bold")).pack(pady=(0, 10))
        
        # Results tabs
        self.results_notebook = ttk.Notebook(parent)
        self.results_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Summary tab
        summary_frame = ttk.Frame(self.results_notebook, padding="10")
        self.results_notebook.add(summary_frame, text="Summary")
        
        # Create a treeview for the summary
        columns = ("agent", "scenario", "score", "survival", "kills", "accuracy")
        self.summary_tree = ttk.Treeview(summary_frame, columns=columns, show="headings")
        
        # Configure column headings
        self.summary_tree.heading("agent", text="Agent")
        self.summary_tree.heading("scenario", text="Scenario")
        self.summary_tree.heading("score", text="Score")
        self.summary_tree.heading("survival", text="Survival Time")
        self.summary_tree.heading("kills", text="Kills")
        self.summary_tree.heading("accuracy", text="Accuracy")
        
        # Configure column widths
        for col in columns:
            self.summary_tree.column(col, width=100)
        
        # Add a scrollbar
        scrollbar = ttk.Scrollbar(summary_frame, orient=tk.VERTICAL, command=self.summary_tree.yview)
        self.summary_tree.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.summary_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Details tab
        details_frame = ttk.Frame(self.results_notebook, padding="10")
        self.results_notebook.add(details_frame, text="Details")
        
        self.details_text = tk.Text(details_frame, wrap=tk.WORD)
        details_scrollbar = ttk.Scrollbar(details_frame, orient=tk.VERTICAL, command=self.details_text.yview)
        self.details_text.configure(yscrollcommand=details_scrollbar.set)
        
        details_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Charts tab
        charts_frame = ttk.Frame(self.results_notebook, padding="10")
        self.results_notebook.add(charts_frame, text="Charts")
        
        self.chart_canvas = None  # Will be created when needed
    
    def _populate_agent_list(self):
        """Populate the agent selection listbox."""
        self.agent_listbox.delete(0, tk.END)
        for agent_type in self.agent_types:
            self.agent_listbox.insert(tk.END, agent_type)
    
    def _populate_scenario_list(self):
        """Populate the scenario selection listbox."""
        self.scenario_listbox.delete(0, tk.END)
        for scenario in self.scenarios:
            self.scenario_listbox.insert(tk.END, f"{scenario.id}: {scenario.name} ({scenario.difficulty})")
    
    def _get_selected_agents(self):
        """Get the selected agent types."""
        indices = self.agent_listbox.curselection()
        return [self.agent_types[i] for i in indices]
    
    def _get_selected_scenarios(self):
        """Get the IDs of the selected scenarios."""
        indices = self.scenario_listbox.curselection()
        return [self.scenarios[i].id for i in indices]
    
    def _run_single_benchmark(self):
        """Run a single benchmark with one agent and one scenario."""
        agent_types = self._get_selected_agents()
        scenario_ids = self._get_selected_scenarios()
        
        if not agent_types:
            messagebox.showerror("Error", "Please select an agent")
            return
        
        if not scenario_ids:
            messagebox.showerror("Error", "Please select a scenario")
            return
        
        if len(agent_types) > 1:
            messagebox.showerror("Error", "Please select only one agent for a single benchmark")
            return
        
        if len(scenario_ids) > 1:
            messagebox.showerror("Error", "Please select only one scenario for a single benchmark")
            return
        
        # Start the benchmark in a separate thread
        self._start_benchmark_thread(self._run_single_benchmark_thread, agent_types[0], scenario_ids[0])
    
    def _run_single_benchmark_thread(self, agent_type, scenario_id):
        """Thread function for running a single benchmark."""
        try:
            self.status_var.set(f"Running benchmark: {agent_type} on {scenario_id}")
            self.progress_var.set(0)
            
            # Create the agent
            agent = create_agent(agent_type)
            if not agent:
                raise ValueError(f"Failed to create agent: {agent_type}")
            
            # Run the benchmark
            result = self.runner.run_single_benchmark(agent, scenario_id)
            
            # Update the UI
            self.progress_var.set(100)
            
            if result["success"]:
                self.status_var.set(f"Benchmark completed: Score {result['score']:.2f}")
                
                # Store the result
                if agent_type not in self.results:
                    self.results[agent_type] = []
                self.results[agent_type].append(result)
                
                # Update the results display
                self._update_results_display()
            else:
                self.status_var.set(f"Benchmark failed: {result.get('error', 'Unknown error')}")
                messagebox.showerror("Benchmark Failed", result.get('error', 'Unknown error'))
        
        except Exception as e:
            self.logger.error(f"Error running benchmark: {str(e)}")
            self.status_var.set(f"Error: {str(e)}")
            messagebox.showerror("Error", f"Failed to run benchmark: {str(e)}")
        
        finally:
            self.active_benchmark = False
    
    def _run_batch_benchmark(self):
        """Run batch benchmarks with multiple agents and scenarios."""
        agent_types = self._get_selected_agents()
        scenario_ids = self._get_selected_scenarios()
        
        if not agent_types:
            messagebox.showerror("Error", "Please select at least one agent")
            return
        
        if not scenario_ids:
            messagebox.showerror("Error", "Please select at least one scenario")
            return
        
        # Confirm if lots of benchmarks
        total_benchmarks = len(agent_types) * len(scenario_ids)
        if total_benchmarks > 10:
            if not messagebox.askyesno("Confirm", 
                                     f"This will run {total_benchmarks} benchmarks. Continue?"):
                return
        
        # Start the benchmark in a separate thread
        self._start_benchmark_thread(self._run_batch_benchmark_thread, agent_types, scenario_ids)
    
    def _run_batch_benchmark_thread(self, agent_types, scenario_ids):
        """Thread function for running batch benchmarks."""
        try:
            total_benchmarks = len(agent_types) * len(scenario_ids)
            completed = 0
            
            for agent_type in agent_types:
                # Create the agent
                agent = create_agent(agent_type)
                if not agent:
                    self.logger.warning(f"Failed to create agent: {agent_type}")
                    continue
                
                for scenario_id in scenario_ids:
                    # Update status
                    self.status_var.set(f"Running benchmark {completed+1}/{total_benchmarks}: " +
                                      f"{agent_type} on {scenario_id}")
                    self.progress_var.set((completed / total_benchmarks) * 100)
                    
                    # Run the benchmark
                    result = self.runner.run_single_benchmark(agent, scenario_id)
                    
                    if result["success"]:
                        # Store the result
                        if agent_type not in self.results:
                            self.results[agent_type] = []
                        self.results[agent_type].append(result)
                    
                    completed += 1
            
            # Update the UI
            self.progress_var.set(100)
            self.status_var.set(f"Batch benchmarks completed: {completed}/{total_benchmarks}")
            
            # Update the results display
            self._update_results_display()
            
            # Show completion message
            if completed < total_benchmarks:
                messagebox.showwarning("Batch Complete", 
                                     f"Completed {completed} of {total_benchmarks} benchmarks")
            else:
                messagebox.showinfo("Batch Complete", 
                                  f"All {total_benchmarks} benchmarks completed successfully")
        
        except Exception as e:
            self.logger.error(f"Error running batch benchmark: {str(e)}")
            self.status_var.set(f"Error: {str(e)}")
            messagebox.showerror("Error", f"Failed to run batch benchmark: {str(e)}")
        
        finally:
            self.active_benchmark = False
    
    def _run_agent_comparison(self):
        """Run a comparison benchmark with multiple agents on a single scenario."""
        agent_types = self._get_selected_agents()
        scenario_ids = self._get_selected_scenarios()
        
        if len(agent_types) < 2:
            messagebox.showerror("Error", "Please select at least two agents for comparison")
            return
        
        if not scenario_ids:
            messagebox.showerror("Error", "Please select a scenario")
            return
        
        if len(scenario_ids) > 1:
            messagebox.showerror("Error", "Please select only one scenario for agent comparison")
            return
        
        # Start the benchmark in a separate thread
        self._start_benchmark_thread(self._run_agent_comparison_thread, agent_types, scenario_ids[0])
    
    def _run_agent_comparison_thread(self, agent_types, scenario_id):
        """Thread function for running agent comparison."""
        try:
            self.status_var.set(f"Running comparison benchmark on {scenario_id}")
            self.progress_var.set(0)
            
            # Create the agents
            agents = []
            for agent_type in agent_types:
                agent = create_agent(agent_type)
                if agent:
                    agents.append(agent)
                else:
                    self.logger.warning(f"Failed to create agent: {agent_type}")
            
            if not agents:
                raise ValueError("Failed to create any agents")
            
            # Run the comparison
            comparison = self.runner.run_agent_comparison(agents, scenario_id)
            
            # Update the UI
            self.progress_var.set(100)
            self.status_var.set(f"Comparison completed: {len(comparison['agents'])} agents")
            
            # Update the results display with comparison
            self._display_comparison_results(comparison)
        
        except Exception as e:
            self.logger.error(f"Error running comparison: {str(e)}")
            self.status_var.set(f"Error: {str(e)}")
            messagebox.showerror("Error", f"Failed to run comparison: {str(e)}")
        
        finally:
            self.active_benchmark = False
    
    def _run_progression_benchmark(self):
        """Run a progression benchmark for a single agent."""
        agent_types = self._get_selected_agents()
        
        if not agent_types:
            messagebox.showerror("Error", "Please select an agent")
            return
        
        if len(agent_types) > 1:
            messagebox.showerror("Error", "Please select only one agent for a progression benchmark")
            return
        
        focus_area = self.focus_var.get()
        
        # Start the benchmark in a separate thread
        self._start_benchmark_thread(self._run_progression_benchmark_thread, agent_types[0], focus_area)
    
    def _run_progression_benchmark_thread(self, agent_type, focus_area):
        """Thread function for running progression benchmark."""
        try:
            self.status_var.set(f"Running progression benchmark for {agent_type} ({focus_area})")
            self.progress_var.set(0)
            
            # Create the agent
            agent = create_agent(agent_type)
            if not agent:
                raise ValueError(f"Failed to create agent: {agent_type}")
            
            # Run the progression
            progression = self.runner.run_agent_progression(agent, focus_area)
            
            # Update the UI
            self.progress_var.set(100)
            
            if progression and "results" in progression:
                success_rate = progression.get("success_rate", 0)
                max_difficulty = progression.get("max_difficulty_completed", "none")
                
                self.status_var.set(
                    f"Progression completed: Success rate {success_rate:.0%}, Max difficulty: {max_difficulty}")
                
                # Display progression results
                self._display_progression_results(progression)
            else:
                self.status_var.set("Progression failed: No results")
                messagebox.showerror("Progression Failed", "No results were generated")
        
        except Exception as e:
            self.logger.error(f"Error running progression: {str(e)}")
            self.status_var.set(f"Error: {str(e)}")
            messagebox.showerror("Error", f"Failed to run progression: {str(e)}")
        
        finally:
            self.active_benchmark = False
    
    def _start_benchmark_thread(self, target_func, *args):
        """Start a benchmark in a separate thread."""
        if self.active_benchmark:
            messagebox.showerror("Error", "A benchmark is already running")
            return
        
        self.active_benchmark = True
        self.benchmark_thread = threading.Thread(target=target_func, args=args)
        self.benchmark_thread.daemon = True
        self.benchmark_thread.start()
    
    def _update_results_display(self):
        """Update the results display with the latest benchmark results."""
        # Clear the treeview
        for item in self.summary_tree.get_children():
            self.summary_tree.delete(item)
        
        # Add all results to the treeview
        for agent_type, results in self.results.items():
            for result in results:
                if result["success"]:
                    self.summary_tree.insert("", tk.END, values=(
                        agent_type,
                        result["scenario_id"],
                        f"{result['score']:.2f}",
                        f"{result['survival_time']:.2f}s",
                        result["kills"],
                        f"{result['accuracy']:.2%}"
                    ))
        
        # Generate a simple chart
        self._update_results_chart()
    
    def _update_results_chart(self):
        """Update the results chart with the latest benchmark results."""
        # Create a new figure
        plt.close('all')
        fig = plt.figure(figsize=(8, 6))
        ax = fig.add_subplot(111)
        
        # Collect data for the chart
        agent_types = []
        scores = []
        
        for agent_type, results in self.results.items():
            for result in results:
                if result["success"]:
                    agent_types.append(agent_type)
                    scores.append(result["score"])
        
        if not agent_types:
            return  # No data to chart
        
        # Create the bar chart
        bars = ax.bar(agent_types, scores)
        
        # Add labels and title
        ax.set_xlabel('Agent Type')
        ax.set_ylabel('Score')
        ax.set_title('Benchmark Scores by Agent')
        
        # Add the chart to the UI
        self._add_chart_to_ui(fig)
    
    def _display_comparison_results(self, comparison):
        """Display the results of an agent comparison."""
        # Update the summary treeview
        for item in self.summary_tree.get_children():
            self.summary_tree.delete(item)
        
        for agent in comparison["agents"]:
            self.summary_tree.insert("", tk.END, values=(
                agent["agent_type"],
                comparison["scenario_id"],
                f"{agent['score']:.2f}",
                f"{agent['survival_time']:.2f}s",
                agent["kills"],
                f"{agent['accuracy']:.2%}"
            ))
        
        # Create a comparison chart
        plt.close('all')
        fig = plt.figure(figsize=(10, 6))
        
        # Score comparison
        ax1 = fig.add_subplot(121)
        agent_types = [a["agent_type"] for a in comparison["agents"]]
        scores = [a["score"] for a in comparison["agents"]]
        
        bars = ax1.bar(agent_types, scores)
        ax1.set_xlabel('Agent Type')
        ax1.set_ylabel('Score')
        ax1.set_title('Score Comparison')
        
        # Survival time comparison
        ax2 = fig.add_subplot(122)
        survival_times = [a["survival_time"] for a in comparison["agents"]]
        
        bars = ax2.bar(agent_types, survival_times)
        ax2.set_xlabel('Agent Type')
        ax2.set_ylabel('Survival Time (s)')
        ax2.set_title('Survival Time Comparison')
        
        fig.tight_layout()
        
        # Add the chart to the UI
        self._add_chart_to_ui(fig)
        
        # Switch to the Charts tab
        self.results_notebook.select(2)  # Index 2 is the Charts tab
    
    def _display_progression_results(self, progression):
        """Display the results of a progression benchmark."""
        # Update the details text
        self.details_text.delete(1.0, tk.END)
        
        self.details_text.insert(tk.END, f"Progression Results for {progression['agent_type']}\n\n")
        self.details_text.insert(tk.END, f"Focus Area: {progression['focus_area']}\n")
        self.details_text.insert(tk.END, f"Success Rate: {progression.get('success_rate', 0):.0%}\n")
        self.details_text.insert(tk.END, f"Max Difficulty Completed: {progression.get('max_difficulty_completed', 'none')}\n\n")
        
        self.details_text.insert(tk.END, "Scenario Results:\n")
        for result in progression.get("results", []):
            success = "✓" if result.get("success", False) else "✗"
            self.details_text.insert(tk.END, f"{success} {result['scenario_id']}: Score {result['score']:.2f}\n")
        
        # Create a progression chart
        plt.close('all')
        fig = plt.figure(figsize=(8, 6))
        ax = fig.add_subplot(111)
        
        # Extract data for the chart
        scenario_ids = []
        scores = []
        success_threshold = []
        
        for result in progression.get("results", []):
            scenario_ids.append(result["scenario_id"])
            scores.append(result["score"])
            
            # Get the success threshold for the scenario
            scenario = self.scenario_library.get_scenario(result["scenario_id"])
            if scenario:
                success_threshold.append(scenario.success_threshold)
            else:
                success_threshold.append(0)
        
        if not scenario_ids:
            return  # No data to chart
        
        # Plot scores
        ax.bar(scenario_ids, scores, label='Score')
        
        # Plot success thresholds
        ax.plot(scenario_ids, success_threshold, 'r--', label='Success Threshold')
        
        # Add labels and title
        ax.set_xlabel('Scenario')
        ax.set_ylabel('Score')
        ax.set_title(f'Progression Scores: {progression["agent_type"]} ({progression["focus_area"]})')
        ax.legend()
        
        # Rotate x-axis labels for readability
        plt.xticks(rotation=45, ha='right')
        
        fig.tight_layout()
        
        # Add the chart to the UI
        self._add_chart_to_ui(fig)
        
        # Switch to the Details tab
        self.results_notebook.select(1)  # Index 1 is the Details tab
    
    def _add_chart_to_ui(self, fig):
        """Add a matplotlib figure to the UI."""
        # Get the charts frame
        charts_frame = self.results_notebook.nametowidget(self.results_notebook.tabs()[2])
        
        # Clear the existing chart if any
        for widget in charts_frame.winfo_children():
            widget.destroy()
        
        # Create a canvas for the figure
        canvas = FigureCanvasTkAgg(fig, master=charts_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Save a reference to the canvas
        self.chart_canvas = canvas
    
    def _save_results(self):
        """Save benchmark results to a file."""
        if not self.results:
            messagebox.showwarning("No Results", "There are no results to save")
            return
        
        # Ask for a file to save to
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filename:
            return  # User canceled
        
        try:
            # Save the report to the selected file
            report = self.runner.generate_report(output_file=filename)
            messagebox.showinfo("Report Saved", f"Benchmark report saved to {filename}")
        except Exception as e:
            self.logger.error(f"Error saving results: {str(e)}")
            messagebox.showerror("Error", f"Failed to save results: {str(e)}")
    
    def _load_results(self):
        """Load benchmark results from a file."""
        # This would load previous benchmark results
        # Not implemented in this simple version
        messagebox.showinfo("Not Implemented", "Loading previous results is not implemented in this version")
    
    def _generate_report(self):
        """Generate a summary report of all benchmark results."""
        if not self.results:
            messagebox.showwarning("No Results", "There are no results to generate a report from")
            return
        
        # Ask for a file to save to
        filename = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not filename:
            return  # User canceled
        
        try:
            # Generate the report
            report = self.runner.generate_report(output_file=filename)
            
            # Show the report in the details text
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(tk.END, report)
            
            # Switch to the Details tab
            self.results_notebook.select(1)  # Index 1 is the Details tab
            
            messagebox.showinfo("Report Generated", f"Benchmark report saved to {filename}")
        except Exception as e:
            self.logger.error(f"Error generating report: {str(e)}")
            messagebox.showerror("Error", f"Failed to generate report: {str(e)}")
    
    def _generate_graphs(self):
        """Generate performance graphs for all benchmarked agents."""
        if not self.results:
            messagebox.showwarning("No Results", "There are no results to generate graphs from")
            return
        
        # Ask for a directory to save to
        dirname = filedialog.askdirectory()
        
        if not dirname:
            return  # User canceled
        
        try:
            # Generate the graphs
            graph_files = self.runner.generate_performance_graphs()
            
            if graph_files:
                messagebox.showinfo("Graphs Generated", 
                                  f"Generated {len(graph_files)} performance graphs in {dirname}")
            else:
                messagebox.showwarning("No Graphs", "No performance graphs were generated")
        except Exception as e:
            self.logger.error(f"Error generating graphs: {str(e)}")
            messagebox.showerror("Error", f"Failed to generate graphs: {str(e)}")
    
    def _show_about(self):
        """Show information about the application."""
        messagebox.showinfo("About", 
                          "Agent Benchmark Tool\n\n" +
                          "A tool for benchmarking and comparing agent performance\n" +
                          "across various scenarios.")


# Run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = BenchmarkUI(root)
    root.mainloop() 