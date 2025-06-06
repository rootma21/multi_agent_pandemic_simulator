#!/usr/bin/env python3
"""
Run and Visualize Agent Health States by Cohort
--------------------------------------------
This script loads trained agent Q-tables from pickle files and runs a single
28-day episode to visualize agent health states by cohort.

NOTE: This header and parts of the code were written with the assistance of generative AI.

Usage:
    python cohorts_viz.py

Results are saved to a PNG file with a timestamp in the filename.

Authors: rootma21, VivekRkay24, saswata0502, DhanyaSNaik
Last updated: April 18th, 2025
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import datetime
from collections import defaultdict

from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
from pandemic_cohorts import InfectionEnv, save_results, save_cohort_statistics

def run_simulation():
    """
    Run the pandemic simulation with 100 agents for 1000 episodes and 
    save the final Q-tables
    """
    # Parameters
    num_episodes = 1000
    num_people = 100
    max_steps = 28
    epsilon_start = 1.0
    epsilon_end = 0.01
    decay_rate = (epsilon_end / epsilon_start) ** (1 / num_episodes)
    gamma = 0.9
    alpha = 0.1
    save_dir = "simulation_results"
    cohort_stats_dir = "cohort_stats"
    
    os.makedirs(save_dir, exist_ok=True)
    os.makedirs(cohort_stats_dir, exist_ok=True)
    
    env = InfectionEnv(
        num_people=num_people,
        max_steps=max_steps,
        decay_rate=decay_rate,
        epsilon=epsilon_start,
        gamma=gamma,
        alpha=alpha
    )
    
    all_stats = {
        'episode_rewards': [],
        'infection_rates': [],
        'death_rates': [],
        'vaccination_rates': [],
        'mask_usage_rates': [],
        'avg_social_contacts': [],
        'cohort_stats': {}
    }
    
    print(f"Starting simulation with {num_people} agents for {num_episodes} episodes...")
    
    for episode in range(num_episodes):
        obs, info = env.reset()
        episode_reward = 0
        
        for day in range(max_steps):
            actions = [person.choose_action() for person in env.people]
            obs, reward, terminated, truncated, info = env.step(actions)
            episode_reward += reward
            
            if terminated or truncated:
                break
        
        all_stats['episode_rewards'].append(episode_reward)
        num_infected = sum(1 for p in env.people if p.health == "infected")
        num_dead = sum(1 for p in env.people if p.health == "dead")
        avg_vaccination = np.mean([p.vaccinated for p in env.people if p.health != "dead"]) if any(p.health != "dead" for p in env.people) else 0
        avg_mask = env.avg_mask_usage
        avg_contacts = np.mean([p.social_contacts for p in env.people if p.health != "dead"]) if any(p.health != "dead" for p in env.people) else 0
        
        all_stats['infection_rates'].append(num_infected / num_people)
        all_stats['death_rates'].append(num_dead / num_people)
        all_stats['vaccination_rates'].append(avg_vaccination)
        all_stats['mask_usage_rates'].append(avg_mask)
        all_stats['avg_social_contacts'].append(avg_contacts)
        all_stats['cohort_stats'][episode + 1] = env.get_cohort_statistics()
        
        env.decay_epsilon()
        

        if (episode + 1) % 100 == 0:
            avg_reward = sum(all_stats['episode_rewards'][-100:]) / 100
            avg_infections = sum(all_stats['infection_rates'][-100:]) / 100
            avg_deaths = sum(all_stats['death_rates'][-100:]) / 100
            print(f"Episode {episode+1}/{num_episodes} | "
                  f"Avg Reward: {avg_reward:.2f} | "
                  f"Avg Infections: {avg_infections:.2%} | "
                  f"Avg Deaths: {avg_deaths:.2%}")
    
    final_files = save_results(env, all_stats, num_episodes, save_dir)
    save_cohort_statistics(env, all_stats, cohort_stats_dir)
    
    print("Simulation complete!")
    print(f"Final results saved to: {final_files}")
    
    q_tables = {}
    for i, person in enumerate(env.people):
        q_tables[f"agent_{i}"] = person.q_table
    
    return env, q_tables, all_stats

def run_visualization_episode(env, q_tables):
    """
    Run a single episode using the learned Q-tables and visualize the results
    """
    obs, info = env.reset()
    
    for i, person in enumerate(env.people):
        if f"agent_{i}" in q_tables:
            person.q_table = q_tables[f"agent_{i}"]
            person.epsilon = 0
    
    print("Running visualization episode with learned policies...")
    
    for day in range(env.max_steps):
        actions = [person.choose_action() for person in env.people]
        obs, reward, terminated, truncated, info = env.step(actions)
        
        if day % 7 == 0:
            num_susceptible = sum(1 for p in env.people if p.health == "susceptible")
            num_exposed = sum(1 for p in env.people if p.health == "exposed")
            num_infected = sum(1 for p in env.people if p.health == "infected")
            num_recovered = sum(1 for p in env.people if p.health == "recovered")
            num_dead = sum(1 for p in env.people if p.health == "dead")
            
            print(f"Day {day}: S={num_susceptible}, E={num_exposed}, I={num_infected}, "
                  f"R={num_recovered}, D={num_dead}")
        
        if terminated or truncated:
            break
    
    print(f"Final Day {env.current_step}:")
    env.render()
    
    visualize_agents_by_cohort(env)
    
def visualize_agents_by_cohort(env):
    """
    Create a visualization with 3 clusters, one for each cohort,
    and represent each agent by their health state with different colors.
    """
    health_colors = {
        "susceptible": "blue",
        "exposed": "orange",
        "infected": "red",
        "recovered": "green",
        "dead": "black"
    }
    
    plt.figure(figsize=(12, 8))
    
    cohort_centers = [
        (-5, 0),  # Cohort 0 (Science Followers)
        (0, 0),   # Cohort 1 (Moderates)
        (5, 0)    # Cohort 2 (Freedom Prioritizers)
    ]
    
    for person in env.people:
        center_x, center_y = cohort_centers[person.cohort_id]
        
        x = center_x + np.random.normal(0, 1)
        y = center_y + np.random.normal(0, 1)
        
        plt.scatter(x, y, color=health_colors[person.health], s=100, alpha=0.7)
    
    for i, (x, y) in enumerate(cohort_centers):
        cohort_name = env.cohort_profiles[i]['name']
        plt.annotate(cohort_name, (x, -2.5), fontsize=14, ha='center')
    
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor=color, markersize=10, label=state)
        for state, color in health_colors.items()
    ]
    plt.legend(handles=legend_elements, title="Health States", loc="upper right", fontsize=12)
    
    plt.title("Agent Health States by Cohort after Pandemic Simulation", fontsize=16)
    plt.xlabel("Cohort Grouping (Position is arbitrary)", fontsize=12)
    plt.ylabel("", fontsize=12)
    
    plt.xticks([])
    plt.yticks([])
    
    stats_text = []
    for i, profile in enumerate(env.cohort_profiles):
        cohort_members = [p for p in env.people if p.cohort_id == i]
        total = len(cohort_members)
        if total == 0:
            continue
            
        susceptible = sum(1 for p in cohort_members if p.health == "susceptible")
        exposed = sum(1 for p in cohort_members if p.health == "exposed")
        infected = sum(1 for p in cohort_members if p.health == "infected")
        recovered = sum(1 for p in cohort_members if p.health == "recovered")
        dead = sum(1 for p in cohort_members if p.health == "dead")
        
        stats = f"{profile['name']} (n={total}):\n"
        stats += f"S: {susceptible} ({susceptible/total:.1%}), "
        stats += f"E: {exposed} ({exposed/total:.1%}), "
        stats += f"I: {infected} ({infected/total:.1%}),\n"
        stats += f"R: {recovered} ({recovered/total:.1%}), "
        stats += f"D: {dead} ({dead/total:.1%})"
        
        stats_text.append(stats)
    
    plt.figtext(0.1, 0.02, stats_text[0], fontsize=10)
    plt.figtext(0.4, 0.02, stats_text[1], fontsize=10)
    plt.figtext(0.7, 0.02, stats_text[2], fontsize=10)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    plt.savefig(f"cohort_visualization_{timestamp}.png", dpi=300, bbox_inches='tight')
    print(f"Visualization saved to cohort_visualization_{timestamp}.png")
    
    plt.tight_layout()
    plt.show()

def main():
    """
    Main function to run simulation and visualization
    """
    env, q_tables, stats = run_simulation()
    
    run_visualization_episode(env, q_tables)

if __name__ == "__main__":
    main()