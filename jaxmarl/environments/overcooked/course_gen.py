from overcooked import Actions
import random
import os
import json


def generate_random_actions(n):
    """
    Generate two lists of n randomly generated actions from the Actions enumeration.

    Parameters:
        n (int): Number of actions to generate.

    Returns:
        tuple: Two lists of randomly generated actions.
    """
    actions_1 = [random.randint(0, 5) for _ in range(n)]
    actions_2 = [random.randint(0, 5) for _ in range(n)]
    return actions_1, actions_2  # Return list of action pairs



def write_actions_to_file(actions_1, actions_2, filename):
    """
    Write the pairs of action lists to a file using JSON serialization.

    Parameters:
        actions_1 (list): List of actions for player 1.
        actions_2 (list): List of actions for player 2.
        filename (str): Name of the file to write to.
    """
    mode = 'a' if os.path.exists(filename) else 'w'
    with open(filename, mode) as file:
        action_pairs = {"actions_1": actions_1, "actions_2": actions_2}
        json.dump(action_pairs, file)
        file.write("\n")  # Write a newline character after each pair

def read_all_actions_from_file(filename):
    """
    Read the pairs of action lists from a file using JSON deserialization.

    Parameters:
        filename (str): Name of the file to read from.

    Returns:
        list or None: List of dictionaries representing pairs of actions for player 1 and player 2,
                      or None if the file is empty.
    """
    try:
        with open(filename, 'r') as file:
            data = file.readlines()
            action_pairs = [json.loads(line.strip()) for line in data if line.strip()]
            return action_pairs if action_pairs else None
    except FileNotFoundError:
        print("Error: File not found.")
        return None
    except json.JSONDecodeError as e:
        print("Error decoding JSON:", e)
        return None

def read_action_n_from_file(filename, n):
    """
    Read the pairs of action lists from a file using JSON deserialization and then return only the nth pair from file.

    Parameters:
        filename (str): Name of the file to read from.
        n (int): 0th based index of course pair you want to pull

    Returns:
        dictionary or none: dictionary of pairs of action courses for player 1 and player 2,
                      or None if the file is empty.
    """
    # try:
    action_pairs = read_all_actions_from_file(filename)

    return action_pairs[n] if action_pairs else None

    # except FileNotFoundError:
    #     print("Error: File not found.")
    #     return None
    # except json.JSONDecodeError as e:
    #     print("Error decoding JSON:", e)
    #     return None




# num_actions = 5  # Example number of actions
# random_actions_1, random_actions_2 = generate_random_actions(num_actions)
# print(random_actions_1, random_actions_2)

# # Write random actions to file
# filename = "random_actions.txt"
# write_actions_to_file(random_actions_1, random_actions_2, filename)

# # Read actions back from file
# all_random_actions = read_actions_from_file(filename)

# # Display the random actions read from the file
# print("Random actions read from file:")
# # for actions_pair in all_random_actions:
# print(all_random_actions)
