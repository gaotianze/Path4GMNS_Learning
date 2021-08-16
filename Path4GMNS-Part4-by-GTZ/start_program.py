from tools import *
from accessibility import *

def program():
    network = read_network(load_demand='true', input_dir='./data')
    evaluate_accessibility(network)
    print('完成可达性评估！\n')

if __name__ == "__main__":

    program()

