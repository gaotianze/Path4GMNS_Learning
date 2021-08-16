from tools import *
from colgen import *

def program(assignment_num,column_update_num):
    network = read_network(load_demand='true', input_dir='./data')
    perform_column_generation(assignment_num, column_update_num, network)
    output_columns(network)
    output_link_performance(network)
    print("\n两个结果文件已输出到当前目录！")

if __name__ == "__main__":
    assignment_num = int(input("分配迭代次数？\n"))
    column_update_num=int(input("列生成迭代次数？\n"))
    program(assignment_num,column_update_num)

