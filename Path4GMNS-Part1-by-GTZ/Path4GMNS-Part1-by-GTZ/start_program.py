from tools import *

def program():
    network = read_network(load_demand='False', input_dir='.')
    node1 = int(input("\n输入要寻找最短路的起始点ID："))
    node2 = int(input("输入要寻找最短路的目标点ID："))
    print(f'\n(node id)从{node1} 到 {node2} 的最短路, ' + network.find_shortest_path(node1, node2))
    with open('time.txt', 'r') as file_to_read:
        print(f'求解用时：{file_to_read.readline()} 秒')

if __name__ == "__main__":
    program()