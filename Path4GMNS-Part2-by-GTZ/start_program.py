from tools import *
from classes import find_path_for_agents
from tools import output_agent_paths

def program():
    network = read_network(load_demand='true', input_dir='./data')
    network.find_path_for_agents()

    dialog_1=''
    while 1:
        dialog_1=input('是否需要输出[agent_paths.csv]？（记载每个agent的目标最短路） [Y/N] ')
        if dialog_1=='Y':
            output_agent_paths(network, False)
        else:
            break

    dialog_2=''
    while 1:
        dialog_2=input('是否需要单独查询某一agent的最短路信息？[Y/N] ')
        agent_id=0
        if dialog_2=='Y':
            agent_id=int(input("要查询的agent ID： "))
            print(f'\n此agent的路径为：从 {network.get_agent_orig_node_id(agent_id)} 到 {network.get_agent_dest_node_id(agent_id)} ')
            print('最短路为(按node id)————'
                  f'{network.get_agent_node_path(agent_id)}')
            print('最短路为(按link id)————'
                  f'{network.get_agent_link_path(agent_id)}\n')
        else:
            break

if __name__ == "__main__":
    program()
