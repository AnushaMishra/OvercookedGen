import os
import jax
import importlib.util

def hyperparam_search(
    rng,
    file_path:str,  # The path to the file to be parameterized
    config:dict,  # Configuration of the alg
    hyper_param_space:dict,  # Hyperparameter space dictionary  
    seeds_per_exp:int=2,  # The number of seeds per experiment, default is 2
    function_name:str='make_train',  # The name of the function to be parameterized, default is 'make_train'
    subfunction_name:str='train',  # The name of the subfunction to be parameterized, default is 'train'
    remove_tmp_file:bool=True,  # Whether to remove the temporary file after use, default is True
    env=None, # jaxmarl env
): 
    """
    Perform a hyperparameter search by creating a new parameterized file from a given file,
    importing the new modified function, and then training the model with the properly vmapped new function.
    """

    # WRITE A NEW PARAMETRIZED FILE
    replacements = {
        **{f'config["{param}"]':param for param in hyper_param_space.keys()},
        **{f"config['{param}']":param for param in hyper_param_space.keys()}
    }
    
    with open(file_path, 'r') as file:
        script = file.readlines()

    new_script = []
    in_function = False
    in_subfuction = False
    for line in script:
        stripped = line.strip()
        if stripped.startswith('def ' + function_name):
            in_function = True
        elif in_function and stripped.startswith('def '+ subfunction_name):
            # Add new parameters to the function definition
            in_subfuction = True
            line = line.replace('):', ', ' + ', '.join(hyper_param_space.keys()) + '):')
        elif stripped == 'return train':
            in_function = False

        if in_subfuction:
            for old, new in replacements.items():
                line = line.replace(old, new)

        new_script.append(line)

    # Create a new file with the 'tmp' suffix
    base, ext = os.path.splitext(file_path)
    new_file_path = base + '_tmp' + ext
    with open(new_file_path, 'w') as file:
        file.writelines(new_script)

    # Import the new, modified function
    spec = importlib.util.spec_from_file_location(function_name, new_file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    new_function = getattr(module, function_name)

    # Delete the temporary file
    if remove_tmp_file:
        os.remove(new_file_path)

    # VMAP THE TRAINING FUNCTION
    if env is not None:
        train_vmapped = new_function(config, env)
    else:
        train_vmapped = new_function(config)
    for i in range(len(hyper_param_space), -1, -1):
        vmap_map = [None]*(len(hyper_param_space)+1)
        vmap_map[i] = 0
        train_vmapped = jax.vmap(train_vmapped, in_axes=vmap_map)

    # TRAIN
    rngs = jax.random.split(rng, seeds_per_exp)
    outs = jax.jit(train_vmapped)(rngs, *hyper_param_space.values())
    
    return outs


def example_qlearning():
    from jaxmarl import make
    from jax import numpy as jnp
    import itertools
    import wandb

    train_script = '/app/JaxMARL/baselines/QLearning/iql.py'

    env = make('switch_riddle')

    config = {
        "NUM_ENVS": 8,
        "NUM_STEPS": 10,
        "BUFFER_SIZE": 5000,
        "BUFFER_BATCH_SIZE": 32,
        "TOTAL_TIMESTEPS": 1e4,
        "AGENT_HIDDEN_DIM": 64,
        "AGENT_INIT_SCALE": 2.0,
        "PARAMETERS_SHARING": True,
        "EPSILON_START": 1.0,
        "EPSILON_FINISH": 0.05,
        "EPSILON_ANNEAL_TIME": 100000,
        "MIXER_EMBEDDING_DIM": 32,
        "MIXER_HYPERNET_HIDDEN_DIM": 64,
        "MIXER_INIT_SCALE": 0.00001,
        "MAX_GRAD_NORM": 20,
        "TARGET_UPDATE_INTERVAL": 200,
        "LR": 0.005,
        "LR_LINEAR_DECAY": False,
        "EPS_ADAM": 0.001,
        "WEIGHT_DECAY_ADAM": 0.00001,
        "TD_LAMBDA_LOSS": False,
        "TD_LAMBDA": 0.6,
        "GAMMA": 0.99,
        "VERBOSE": True,
        "WANDB_ONLINE_REPORT": False,
        "NUM_TEST_EPISODES": 32,
        "TEST_INTERVAL": 1e4,
        "ENTITY": "mttga",
        "PROJECT": "jaxmarl_hyper_tuning",
        "WANDB_MODE" : "online",
    }

    hyper_param_space = {
        'LR':jnp.array([0.01, 0.001, 0.0001]),
        'AGENT_INIT_SCALE':jnp.array([1., 0.1, 0.001])
    }

    outs = hyperparam_search(
        file_path=train_script,
        config=config,
        hyper_param_space=hyper_param_space,
        env=env,
        rng=jax.random.PRNGKey(0)
    )

    # log the results as separate metrics
    log_metrics = {
        'timesteps':outs['metrics']['timesteps'][0],
        'returns':outs['metrics']['rewards']['__all__'].mean(axis=0)
    }

    for idx in itertools.product(*map(lambda x: list(range(len(x))), hyper_param_space.values())):
        label = "_".join(f'{k}={hyper_param_space[k][i]:.5f}' for i, k in zip(idx, hyper_param_space))
        exp_name = f'iql_{label}'

        run = wandb.init(
            entity=config["ENTITY"],
            project=config["PROJECT"],
            tags=["IQL", "RNN"],
            name=exp_name,
            config=config,
            mode=config["WANDB_MODE"],
            group='switch_riddle_ht',
        )

        run_logs = jax.tree_util.tree_map(lambda x: x[idx].tolist(), log_metrics)
        for values in zip(*run_logs.values()):
            run.log({k:v for k, v in zip(run_logs.keys(), values)})

        run.finish()


def example_ippo():

    from jax import numpy as jnp

    train_script = '/app/JaxMARL/baselines/IPPO/ippo_ff_switch_riddle.py'

    config = {
        "ENV_NAME": "switch_riddle",
        "ENV_KWARGS": {},
        "LR": 2.5e-4,
        "NUM_ENVS": 64,
        "NUM_STEPS": 128,
        "TOTAL_TIMESTEPS": 1e6,
        "UPDATE_EPOCHS": 4,
        "NUM_MINIBATCHES": 4,
        "GAMMA": 0.99,
        "GAE_LAMBDA": 0.95,
        "CLIP_EPS": 0.2,
        "ENT_COEF": 0.01,
        "VF_COEF": 0.5,
        "MAX_GRAD_NORM": 0.5,
        "ACTIVATION": "relu",
        "ANNEAL_LR": False,
        "ENTITY": "mttga",
        "PROJECT": "smax",
        "WANDB_MODE" : "online",
    }

    hyper_param_space = {
        'LR':jnp.array([0.01, 0.001, 0.0001]),
        'MAX_GRAD_NORM':jnp.array([10, 1, 0.1])
    }

    outs = hyperparam_search(
        rng=jax.random.PRNGKey(0),
        file_path=train_script,
        config=config,
        hyper_param_space=hyper_param_space,
        seeds_per_exp=2,
    )
    print(outs['metrics']['returned_episode_returns'].shape)
    # not sure how to post-process the ippo outs



if __name__=='__main__':
    example_qlearning()
    #example_ippo()