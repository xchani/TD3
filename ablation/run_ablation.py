# The following scripts run the TD3 algorithm.
import matplotlib.pyplot as plt
import numpy as np
import torch
import gym
import argparse
import os
import torch.nn.functional as F
import utils
import TD3
import DDPG
import TD3_DP
import TD3_TPS
import TD3_CDQ

def eval_policy(policy, env, eval_episodes=10):
    eval_env = gym.make(env)

    avg_reward = 0.
    for _ in range(eval_episodes):
        state, done = eval_env.reset(), False
        while not done:
            action = policy.select_action(np.array(state))
            state, reward, done,_ = eval_env.step(action)
            avg_reward += reward

    avg_reward /= eval_episodes
    #print("---------------------------------------")
    #print(f"Evaluation over {eval_episodes} episodes: {avg_reward:.3f}")
    #print("---------------------------------------")
    return avg_reward


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="TD3")
    parser.add_argument("--env", default="Pendulum-v0")
    args = parser.parse_args()

    env = gym.make(args.env)
    torch.manual_seed(0)
    np.random.seed(0)

    state_dim = env.observation_space.shape[0]
    action_dim = env.action_space.shape[0]
    max_action = env.action_space.high[0]

    args_policy_noise = 0.2
    args_noise_clip = 0.5
    args_policy_freq = 2
    args_max_timesteps = 100000
    args_expl_noise = 0.1
    args_batch_size = 25
    args_eval_freq = 1000
    args_start_timesteps = 0

    kwargs = {
        "state_dim": state_dim,
        "action_dim": action_dim,
        "max_action": max_action,
        "discount": 0.99,
        "tau": 0.005
    }


    # args_policy = 'TD3'

    if args.policy.startswith("TD3"):
        # Target policy smoothing is scaled wrt the action scale
        kwargs["policy_noise"] = args_policy_noise * max_action
        kwargs["noise_clip"] = args_noise_clip * max_action
        kwargs["policy_freq"] = args_policy_freq
        if args.policy == "TD3":
            policy = TD3.TD3(**kwargs)
        elif args.policy == "TD3-DP":
            policy = TD3_DP.TD3(**kwargs)
        elif args.policy == "TD3-TPS":
            policy = TD3_TPS.TD3(**kwargs)
        elif args.policy == "TD3-CDQ":
            policy = TD3_CDQ.TD3(**kwargs)
    elif args.policy == "OurDDPG":
        policy = OurDDPG.DDPG(**kwargs)
    elif args.policy == "DDPG":
        policy = DDPG.DDPG(**kwargs)
    replay_buffer = utils.ReplayBuffer(state_dim, action_dim)

    # Evaluate untrained policy
    evaluations = [eval_policy(policy, args.env)]

    state, done = env.reset(), False
    episode_reward = 0
    episode_timesteps = 0
    episode_num = 0
    counter = 0
    msk_list = []
    temp_curve = [eval_policy(policy, args.env)]
    temp_val = []
    for t in range(int(args_max_timesteps)):
        episode_timesteps += 1
        counter += 1
        # Select action randomly or according to policy
        if t < args_start_timesteps:
            action = np.random.uniform(-max_action,max_action,action_dim)
        else:
            if np.random.uniform(0,1) < 0.1:
                action = np.random.uniform(-max_action,max_action,action_dim)
            else:
                action = (
                    policy.select_action(np.array(state))
                    + np.random.normal(0, max_action * args_expl_noise, size=action_dim)
                ).clip(-max_action, max_action)

        # Perform action
        next_state, reward, done,_ = env.step(action)
        done_bool = float(done) if episode_timesteps < env._max_episode_steps else 0

        replay_buffer.add(state, action, next_state, reward, done_bool)

        state = next_state
        episode_reward += reward

        if t >= args_start_timesteps:
            '''TD3'''
            last_val = 999.
            patient = 5
            for i in range(1):
                policy.train(replay_buffer, args_batch_size)


        # Train agent after collecting sufficient data
        if done:
            print(f"Total T: {t+1} Episode Num: {episode_num+1} Episode T: {episode_timesteps} Reward: {episode_reward:.3f}")
            msk_list = []
            state, done = env.reset(), False
            episode_reward = 0
            episode_timesteps = 0
            episode_num += 1

        # Evaluate episode
        if (t + 1) % args_eval_freq == 0:
            evaluations.append(eval_policy(policy, args.env))
            print('recent Evaluation:',evaluations[-1])
            np.save('results/evaluations_alias{}_ENV{}'.format(args.policy,args.env),evaluations)
