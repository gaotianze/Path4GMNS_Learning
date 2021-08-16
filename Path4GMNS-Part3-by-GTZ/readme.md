Path4GMNS Reproducted By TianzeGao.

Path4GMNS is an open-source, cross-platform, lightweight, and fast Python path engine for networks encoded in GMNS.
Pls visit：https://github.com/jdlph/Path4GMNS

此Repository为 Tianze Gao 于 2021/08 实现的Path4GMNS的功能拆分版，并附上各部分重点函数的用途及原理，用于自我学习与功能了解.

Part3为基于路径进行UE（用户均衡）分配的功能，先解压data文件夹中的运行文件夹中agent.zip，再运行主文件夹下的'start_program.py'.

其他文件作用：
link.csv——存储link数据.
node.csv——存储node数据.
agent.zip——内含agent.csv，由于文件太大，须先解压后使用！！
demand.csv——存储各zone之间的需求数据.
settings.yml——记载agent与程序设置.
bin——内含C++的Dequeue算法dll.
classes.py——定义程序中用到的类.
consts.py——定义常量.
path4agents.py——是本程序中用到的与最短路求解有关的算法，还有为单独agent寻找最短路的前置程序.
tools.py——本程序中用到的工具，含有：读取网络、类型转换等.
colgen.py——列生成算法，用作基于路径的用户均衡交通分配.