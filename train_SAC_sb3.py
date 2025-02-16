import gymnasium as gym
from stable_baselines3 import SAC
import torch
import CarRacingObstacles.obstacle_obj
from CarRacingObstacles.wrappers import wrap_CarRacingObst
from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback
from datetime import datetime
from CarRacingObstacles.utils import EvalCallbackStep, wrap_eval_env
from gymnasium.spaces import Dict, Box


def build_parser():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--pre_trained_mdl', '-ptm', type=str, default=None)

    parser.add_argument('--exp_name', type=str, default='todo')
    # environment para
    parser.add_argument('--env_name', type=str, default="CarRacing-obstaclesV2")
    parser.add_argument('--ep_len', type=int, default=1000)

    # training para
    parser.add_argument('--n_iter', '-n', type=int, default=1000000)
    parser.add_argument('--learning_starts', '-ls', type=int, default=100)  # steps collected per train iteration
    parser.add_argument('--train_batch_size', '-tb', type=int, default=256)  # steps used per gradient step
    parser.add_argument('--replay_buffer_size', '-rbs', type=int, default=1000000)
    parser.add_argument('--init_temperature', '-temp', type=float, default=1.0)
    parser.add_argument('--learning_rate', '-lr', type=float, default=3e-4)
    parser.add_argument('--critic_target_update_frequency', type=int, default=1)
    parser.add_argument('--gamma', type=float, default=0.99)
    parser.add_argument('--train_freq', '-tf', type=int, default=1)
    parser.add_argument('--grad_steps', '-gs', type=int, default=1)
    parser.add_argument('--training_seed', '-seed', type=int, default=None)
    # parser.add_argument('--n_layers', '-l', type=int, default=2)
    # parser.add_argument('--size', '-s', type=int, default=64)

    parser.add_argument('--eval_episodes', '-ee', type=int, default=5)  # steps collected per eval iteration
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--eval_freq', '-eq', type=int, default=10000)

    args = parser.parse_args()
    params = vars(args)
    return params


def train_SAC(params):
    date = datetime.now()
    save_path = "./logs/" + params['env_name'] + f"_{date.month:02}{date.day:02}_{params['exp_name']}"

    if torch.backends.mps.is_available():
        device = torch.device("mps")
    elif torch.cuda.is_available():
        device = torch.device("cuda:0")
    else:
        device = torch.device("cpu")
    print(f"Using device: {device}")

    # Create CarRacing environment
    env = gym.make(params['env_name'], max_episode_steps=params['ep_len'], continuous=True, n_obst=6)
    env = wrap_CarRacingObst(env)
    eval_env = wrap_eval_env(env)

    # policy type
    policy = None
    if isinstance(env.observation_space, Box):
        print("The observation space is a Box (continuous), use CnnPolicy.")
        policy = "CnnPolicy"
    elif isinstance(env.observation_space, Dict):
        print("The observation space is a Dict (dictionary of spaces) use MultiInputPolicy.")
        policy = "MultiInputPolicy"

    # Initialize SAC
    model = SAC(policy=policy,
                env=env,
                learning_rate=params['learning_rate'],  #lambda progress: params['learning_rate'] * progress + 0.0001, #
                buffer_size=params['replay_buffer_size'],
                learning_starts=params['learning_starts'],
                batch_size=params['train_batch_size'],
                gamma=params['gamma'],
                train_freq=params['train_freq'],
                gradient_steps=params['grad_steps'],
                seed=params['training_seed'],
                tensorboard_log=save_path,
                verbose=1,
                device=device)
    print(model.policy.critic)
    print(model.policy.actor)

    if params['pre_trained_mdl']:
        print("Loading pre-trained model")
        mdl_path = "logs/" + params['pre_trained_mdl'] #+ "/best_model.zip"
        model.set_parameters(mdl_path)
        # model = SAC.load(mdl_path, device=device)
        # model.set_env(env)
        # model.tensorboard_log = save_path


    # for evaluation
    eval_callback = EvalCallbackStep(eval_env,
                                     best_model_save_path=save_path,
                                     log_path=save_path,
                                     eval_freq=params['eval_freq'],
                                     n_eval_episodes=params['eval_episodes'],
                                     deterministic=True,
                                     render=False)

    checkpoint_callback = CheckpointCallback(save_freq=100000,
                                             save_path=save_path,
                                             name_prefix="Checkpoint")
    CallBack = [eval_callback, checkpoint_callback]

    # Train the model
    model.learn(total_timesteps=params['n_iter'], callback=CallBack, reset_num_timesteps=True) #

    # Save the model
    # model.save("sac_car_racing")


def main():
    print("START")
    params = build_parser()
    train_SAC(params)


if __name__ == "__main__":
    main()