import os
import csv
import threading

from classes import Node, Link, Network, Column, ColumnVec, VDFPeriod, \
    AgentType, DemandPeriod, Demand, Assignment, UI
from colgen import update_links_using_columns
from consts import MIN_OD_VOL, SMALL_DIVISOR;

_zone_degrees = {}


def read_network(load_demand='true', input_dir='.'):
    assignm = Assignment()
    network = Network()

    read_settings(input_dir, assignm)

    read_nodes(input_dir,
               network.node_list,
               network.node_id_to_no_dict,
               network.node_no_to_id_dict,
               network.zone_to_nodes_dict)

    read_links(input_dir,
               network.link_list,
               network.node_list,
               network.node_id_to_no_dict,
               network.link_id_dict,
               assignm.get_agent_type_count(),
               assignm.get_demand_period_count(),
               load_demand)

    if load_demand:
        for d in assignm.get_demands():
            at = assignm.get_agent_type_id(d.get_agent_type_str())
            dp = assignm.get_demand_period_id(d.get_period())
            read_demand(input_dir,
                        d.get_file_name(),
                        at,
                        dp,
                        network.zone_to_nodes_dict,
                        assignm.column_pool)

    network.update(assignm.get_agent_type_count(),
                   assignm.get_demand_period_count())

    assignm.network = network
    assignm.setup_spnetwork()

    ui = UI(assignm)

    return ui


def read_nodes(input_dir,
               nodes,
               id_to_no_dict,
               no_to_id_dict,
               zone_to_node_dict):
    """ step 1: read input_node """
    with open(input_dir + '/node.csv', 'r', encoding='utf-8') as fp:
        print('读取 node.csv ...')

        reader = csv.DictReader(fp)
        node_seq_no = 0
        for line in reader:
            # set up node_id, which should be an integer
            node_id = _convert_str_to_int(line['node_id'])
            if node_id is None:
                continue

            # set up zone_id, which should be an integer
            zone_id = _convert_str_to_int(line['zone_id'])
            if zone_id is None:
                zone_id = -1

            # treat them as string
            coord_x = line['x_coord']
            coord_y = line['y_coord']

            # construct node object
            node = Node(node_seq_no, node_id, zone_id, coord_x, coord_y)
            nodes.append(node)

            # set up mapping between node_seq_no and node_id
            id_to_no_dict[node_id] = node_seq_no
            no_to_id_dict[node_seq_no] = node_id

            # associate node_id to corresponding zone
            if zone_id not in zone_to_node_dict.keys():
                zone_to_node_dict[zone_id] = []
            zone_to_node_dict[zone_id].append(node_id)

            node_seq_no += 1

        print(f"node的个数为： {node_seq_no}")

        zone_size = len(zone_to_node_dict)
        # do not count virtual zone with id as -1
        if -1 in zone_to_node_dict.keys():
            zone_size -= 1

        print(f"zone的个数为： {zone_size}")


def read_links(input_dir,
               links,
               nodes,
               id_to_no_dict,
               link_id_dict,
               agent_type_size,
               demand_period_size,
               load_demand):
    """ step 2: read input_link """
    with open(input_dir + '/link.csv', 'r', encoding='utf-8') as fp:
        print('读取 link.csv ...')

        reader = csv.DictReader(fp)
        link_seq_no = 0
        for line in reader:
            # it can be an empty string
            link_id = line['link_id']

            # check the validility
            from_node_id = _convert_str_to_int(line['from_node_id'])
            if from_node_id is None:
                continue

            to_node_id = _convert_str_to_int(line['to_node_id'])
            if to_node_id is None:
                continue

            length = _convert_str_to_float(line['length'])
            if length is None:
                continue

            # pass validility check

            try:
                from_node_no = id_to_no_dict[from_node_id]
                to_node_no = id_to_no_dict[to_node_id]
            except KeyError:
                print(f"EXCEPTION: Node ID {from_node_no} "
                      f"or/and Node ID {to_node_id} 不在网络中!!")
                continue

            # for the following attributes,
            # if they are not None, convert them to the corresponding types
            # if they are None's, set them using the default values

            lanes = _convert_str_to_int(line['lanes'])
            if lanes is None:
                lanes = 1

            link_type = _convert_str_to_int(line['link_type'])
            if link_type is None:
                link_type = 1

            free_speed = _convert_str_to_int(line['free_speed'])
            if free_speed is None:
                free_speed = 60

            # issue: int??
            capacity = _convert_str_to_int(line['capacity'])
            if capacity is None:
                capacity = 49500

            # if link.csv does not have no column 'allowed_uses',
            # set allowed_uses to 'auto'
            # developer's note:
            # we may need to change this implemenation as we cannot deal with
            # cases a link which is not open to any modes
            try:
                allowed_uses = line['allowed_uses']
                if not allowed_uses:
                    allowed_uses = 'all'
            except KeyError:
                allowed_uses = 'all'

            # if link.csv does not have no column 'geometry',
            # set geometry to ''
            try:
                geometry = line['geometry']
            except KeyError:
                geometry = ''

            link_id_dict[link_id] = link_seq_no

            # construct link ojbect
            link = Link(link_id,
                        link_seq_no,
                        from_node_no,
                        to_node_no,
                        from_node_id,
                        to_node_id,
                        length,
                        lanes,
                        link_type,
                        free_speed,
                        capacity,
                        allowed_uses,
                        geometry,
                        agent_type_size,
                        demand_period_size)

            # VDF Attributes
            for i in range(demand_period_size):
                header_vdf_alpha = 'VDF_alpha' + str(i + 1)
                header_vdf_beta = 'VDF_beta' + str(i + 1)
                header_vdf_mu = 'VDF_mu' + str(i + 1)
                header_vdf_fftt = 'VDF_fftt' + str(i + 1)
                header_vdf_cap = 'VDF_cap' + str(i + 1)
                header_vdf_phf = 'VDF_phf' + str(i + 1)

                # case i: link.csv does not VDF attributes at all
                # case ii: link.csv only has partial VDF attributes
                # under case i, we will set up only one VDFPeriod ojbect using
                # default values
                # under case ii, we will set up some VDFPeriod ojbects up to
                # the number of complete set of VDF_alpha, VDF_beta, and VDF_mu
                try:
                    VDF_alpha = line[header_vdf_alpha]
                    if VDF_alpha:
                        VDF_alpha = float(VDF_alpha)
                except (KeyError, TypeError):
                    if i == 0:
                        # default value will be applied in the constructor
                        VDF_alpha = 0.15
                    else:
                        break

                try:
                    VDF_beta = line[header_vdf_beta]
                    if VDF_beta:
                        VDF_beta = float(VDF_beta)
                except (KeyError, TypeError):
                    if i == 0:
                        # default value will be applied in the constructor
                        VDF_beta = 4
                    else:
                        break

                try:
                    VDF_mu = line[header_vdf_mu]
                    if VDF_mu:
                        VDF_mu = float(VDF_mu)
                except (KeyError, TypeError):
                    if i == 0:
                        # default value will be applied in the constructor
                        VDF_mu = 1000
                    else:
                        break

                try:
                    VDF_fftt = line[header_vdf_fftt]
                    if VDF_fftt:
                        VDF_fftt = float(VDF_fftt)
                except (KeyError, TypeError):
                    # set it up using length and free_speed from link
                    VDF_fftt = length / max(SMALL_DIVISOR, free_speed) * 60

                try:
                    VDF_cap = line[header_vdf_cap]
                    if VDF_cap:
                        VDF_cap = float(VDF_cap)
                except (KeyError, TypeError):
                    # set it up using capacity from link
                    VDF_cap = capacity

                # not a mandatory column
                try:
                    VDF_phf = line[header_vdf_phf]
                    if VDF_phf:
                        VDF_phf = float(VDF_phf)
                except (KeyError, TypeError):
                    # default value will be applied in the constructor
                    VDF_phf = -1

                # construct VDFPeriod object
                vdf = VDFPeriod(i, VDF_alpha, VDF_beta, VDF_mu,
                                VDF_fftt, VDF_cap, VDF_phf)

                link.vdfperiods.append(vdf)

            # set up outgoing links and incoming links
            # 从link中读完信息之后，给node加上他们的出弧与入弧
            from_node = nodes[from_node_no]
            to_node = nodes[to_node_no]
            from_node.add_outgoing_link(link)
            to_node.add_incoming_link(link)

            links.append(link)

            # set up zone degrees
            if load_demand:
                oz_id = from_node.get_zone_id()
                dz_id = to_node.get_zone_id()
                _update_orig_zone(oz_id)
                _update_dest_zone(dz_id)

            link_seq_no += 1

        print(f"link的个数是： {link_seq_no}")


def read_demand(input_dir,
                file,
                agent_type_id,
                demand_period_id,
                zone_to_node_dict,
                column_pool):
    """ step 3:read input_agent """
    with open(input_dir + '/' + file, 'r', encoding='utf-8') as fp:
        print('读取 demand.csv ...')

        at = agent_type_id
        dp = demand_period_id

        reader = csv.DictReader(fp)
        total_agents = 0
        for line in reader:
            # invalid origin zone id, discard it
            oz_id = _convert_str_to_int(line['o_zone_id'])
            if oz_id is None:
                continue

            # invalid destinationzone id, discard it
            dz_id = _convert_str_to_int(line['d_zone_id'])
            if dz_id is None:
                continue

            # o_zone_id does not exist in node.csv, discard it
            if oz_id not in zone_to_node_dict.keys():
                continue

            # d_zone_id does not exist in node.csv, discard it
            if dz_id not in zone_to_node_dict.keys():
                continue

            volume = _convert_str_to_float(line['volume'])
            if volume is None:
                continue

            if volume == 0:
                continue

            # precheck on connectivity of each OD pair
            if not _are_od_connected(oz_id, dz_id):
                continue

            # set up volume for ColumnVec
            if (at, dp, oz_id, dz_id) not in column_pool.keys():
                column_pool[(at, dp, oz_id, dz_id)] = ColumnVec()
            column_pool[(at, dp, oz_id, dz_id)].od_vol += volume

            total_agents += int(volume + 1)

        # print(f"agent的个数为： {total_agents}")

        if total_agents == 0:
            raise Exception('无有效OD交通量！！ 再次检查 demand.csv ！')


def _convert_str_to_int(str):
    """
    TypeError will take care the case that str is None
    ValueError will take care the case that str is empty
    """
    if not str:
        return None

    try:
        return int(str)
    except ValueError:
        return int(float(str))
    except TypeError:
        return None


def _convert_str_to_float(str):
    """
    TypeError will take care the case that str is None
    ValueError will take care the case that str is empty
    """
    if not str:
        return None

    try:
        return float(str)
    except (TypeError, ValueError):
        return None


def _update_orig_zone(oz_id):
    if oz_id not in _zone_degrees:
        _zone_degrees[oz_id] = 1
    elif _zone_degrees[oz_id] == 2:
        _zone_degrees[oz_id] = 3


def _update_dest_zone(dz_id):
    if dz_id not in _zone_degrees:
        _zone_degrees[dz_id] = 2
    elif _zone_degrees[dz_id] == 1:
        _zone_degrees[dz_id] = 3


def read_settings(input_dir, assignment):
    try:
        import yaml as ym

        with open(input_dir + '/settings.yml') as file:
            settings = ym.full_load(file)

            # agent types
            agents = settings['agents']
            for i, a in enumerate(agents):
                agent_type = a['type']
                agent_name = a['name']
                agent_vot = a['vot']
                agent_flow_type = a['flow_type']
                agent_pce = a['pce']
                agent_ffs = a['free_speed']

                at = AgentType(i,
                               agent_type,
                               agent_name,
                               agent_vot,
                               agent_flow_type,
                               agent_pce,
                               agent_ffs)

                assignment.update_agent_types(at)

            # demand periods
            demand_periods = settings['demand_periods']
            for i, d in enumerate(demand_periods):
                period = d['period']
                time_period = d['time_period']

                dp = DemandPeriod(i, period, time_period)
                assignment.update_demand_periods(dp)

            # demand files
            demands = settings['demand_files']
            for i, d in enumerate(demands):
                demand_file = d['file_name']
                # demand_format_tpye = d['format_type']
                demand_period = d['period']
                demand_type = d['agent_type']

                demand = Demand(i, demand_period, demand_type, demand_file)
                assignment.update_demands(demand)

    except ImportError:
        # just in case user does not have pyyaml installed
        print('下次请您装好 pyyaml 再来嗷!')
        print('下面将会按默认的需求时间与一个默认的agent类初始化引擎，可能不会反应你案例的实际情况!\n')
        _auto_setup(assignment)
    except FileNotFoundError:
        # just in case user does not provide settings.yml
        print('下次请您创建好 settings.yml 再来!')
        print('下面将会按默认的需求时间与一个默认的agent类初始化引擎，可能不会反应你案例的实际情况!\n')
        _auto_setup(assignment)
    except Exception as e:
        raise e


def output_columns(ui, output_geometry=True, output_dir='.'):
    with open(output_dir + '/agent.csv', 'w', newline='') as fp:
        base = ui._base_assignment

        nodes = base.get_nodes()
        links = base.get_links()
        column_pool = base.get_column_pool()

        writer = csv.writer(fp)

        line = ['agent_id',
                'o_zone_id',
                'd_zone_id',
                'path_id',
                'agent_type',
                'demand_period',
                'volume',
                'toll',
                'travel_time',
                'distance',
                'node_sequence',
                'link_sequence',
                'geometry']

        writer.writerow(line)

        path_sep = ';'
        i = 0
        for k, cv in column_pool.items():
            if cv.get_od_volume() <= 0:
                continue

            # k = (at_id, dp_id, oz_id, dz_id)
            at_id = k[0]
            dp_id = k[1]
            oz_id = k[2]
            dz_id = k[3]

            at_str = base.get_agent_type_str(at_id)
            dp_str = base.get_demand_period_str(dp_id)

            for col in cv.get_columns().values():
                i += 1
                node_seq = path_sep.join(
                    str(nodes[x].get_node_id()) for x in reversed(col.nodes)
                )
                link_seq = path_sep.join(
                    str(links[x].get_link_id()) for x in reversed(col.links)
                )

                geometry = ''
                if output_geometry:
                    geometry = ', '.join(
                        nodes[x].get_coordinate() for x in reversed(col.nodes)
                    )
                    geometry = 'LINESTRING (' + geometry + ')'

                line = [i,
                        oz_id,
                        dz_id,
                        col.get_seq_no(),
                        at_str,
                        dp_str,
                        col.get_volume(),
                        col.get_toll(),
                        col.get_travel_time(),
                        col.get_distance(),
                        node_seq,
                        link_seq,
                        geometry]

                writer.writerow(line)

        # if output_dir == '.':
        #     print('\ncheck agent.csv in '
        #           + os.getcwd() + ' for path finding results')
        # else:
        #     print('\ncheck agent.csv in '
        #           + os.path.join(os.getcwd(), output_dir)
        #           + ' for path finding results')


def output_link_performance(ui, output_dir='.'):
    with open(output_dir + '/link_performance.csv', 'w', newline='') as fp:
        base = ui._base_assignment

        links = base.get_links()

        writer = csv.writer(fp)

        line = ['link_id',
                'from_node_id',
                'to_node_id',
                'time_period',
                'volume',
                'travel_time',
                'speed',
                'VOC',
                'queue',
                'density',
                'geometry',
                'notes']

        writer.writerow(line)

        for link in links:
            for dp in base.get_demand_periods():
                avg_travel_time = link.get_period_avg_travel_time(dp.get_id())
                speed = link.get_length() / (max(SMALL_DIVISOR, avg_travel_time) / 60)

                line = [link.get_link_id(),
                        link.get_from_node_id(),
                        link.get_to_node_id(),
                        dp.get_period(),
                        link.get_period_flow_vol(dp.get_id()),
                        avg_travel_time,
                        speed,
                        link.get_period_voc(dp.get_id()),
                        '',
                        '',
                        link.get_geometry(),
                        '']

                writer.writerow(line)

        # if output_dir == '.':
        #     print('\ncheck link_performance.csv in '
        #           + os.getcwd() + ' for link performance')
        # else:
        #     print('\ncheck link_performance.csv in '
        #           + os.path.join(os.getcwd(), output_dir)
        #           + ' for link performance')


def load_columns(ui, input_dir='.'):
    """ developer note: do we use agent.csv to set up network? """
    with open(input_dir + '/agent.csv', 'r') as f:
        print('read agent.csv')

        A = ui._base_assignment

        reader = csv.DictReader(f)

        # just in case agent_id was not outputed
        last_agent_id = 0
        for line in reader:
            # critical info
            oz_id = _convert_str_to_int(line['o_zone_id'])
            if oz_id is None:
                continue

            dz_id = _convert_str_to_int(line['d_zone_id'])
            if dz_id is None:
                continue

            node_seq = line['node_sequence']
            if node_seq is None:
                continue

            link_seq = line['link_sequence']
            if link_seq is None:
                continue

            # non-critical info
            agent_id = _convert_str_to_int(line['agent_id'])
            if agent_id is None:
                agent_id = last_agent_id + 1

            last_agent_id = agent_id

            # it could be empty
            # path_id = line['path_id']

            at = line['agent_type']
            if not at:
                continue
            else:
                at = A.get_agent_type_id(at)

            dp = line['demand_period']
            if not dp:
                continue
            else:
                dp = A.get_demand_period_id(dp)

            vol = _convert_str_to_float(line['volume'])
            if vol is None:
                continue

            toll = _convert_str_to_float(line['toll'])
            if toll is None:
                toll = 0

            tt = _convert_str_to_float(line['travel_time'])
            if tt is None:
                tt = 0

            dist = _convert_str_to_float(line['distance'])
            if dist is None:
                dist = 0

            # it could be empty
            geo = line['geometry']

            if (at, dp, oz_id, dz_id) not in A.get_column_pool().keys():
                continue

            cv = A.get_column_vec(at, dp, oz_id, dz_id)

            node_path = None
            try:
                # if x is only needed for columns generated from DTALite,
                # which have the trailing ';' and leads to '' after split
                node_path = [int(x) for x in node_seq.split(';') if x]
            except ValueError:
                raise Exception(
                    f'INVALID NODE PATH found for agent id: {agent_id}'
                )

            node_sum = sum(node_path)

            if node_sum not in cv.path_node_seq_map.keys():
                path_seq_no = cv.get_column_num()
                col = Column(path_seq_no)

                try:
                    col.nodes = [A.get_node_no(x) for x in node_path]
                except IndexError:
                    raise Exception(
                        'Invalid node found on column!!'
                        'Did you use agent.csv from a different network?'
                    )

                try:
                    # if x is only needed for columns generated from DTALite,
                    # which have the trailing ';' and leads to '' after split
                    col.links = [
                        A.get_link_seq_no(x) for x in link_seq.split(';') if x
                    ]
                except IndexError:
                    raise Exception(
                        'INVALID link found on column!!'
                        'Did you use agent.csv from a different network?'
                    )
                except ValueError:
                    raise Exception(
                        f'INVALID LINK PATH found for agent id: {agent_id}'
                    )

                # the following four are non-critical info
                col.set_toll(toll)
                col.set_travel_time(tt)
                col.set_geometry(geo)

                if dist == 0:
                    sum(A.get_link(x).get_length() for x in col.links)
                col.set_distance(dist)

                cv.add_new_column(node_sum, col)

            cv.get_column(node_sum).increase_volume(vol)

        update_links_using_columns(ui)


def _are_od_connected(oz_id, dz_id):
    connected = True

    # at least one node in O must have outgoing links
    if oz_id not in _zone_degrees or _zone_degrees[oz_id] == 2:
        connected = False
        print(f'WARNING! {oz_id} has no outgoing links to route volume '
              f'between OD: {oz_id} --> {dz_id}')

    # at least one node in D must have incoming links
    if dz_id not in _zone_degrees or _zone_degrees[dz_id] == 1:
        if connected:
            connected = False
        print(f'WARNING! {dz_id} has no incoming links to route volume '
              f'between OD: {oz_id} --> {dz_id}')

    return connected


def _auto_setup(assignment):
    """ automatically set up one demand period and one agent type

    The two objects will be set up using the default construnctors using the
    default values. See class DemandPeriod and class AgentType for details
    """
    at = AgentType()
    dp = DemandPeriod()
    d = Demand()

    assignment.update_agent_types(at)
    assignment.update_demand_periods(dp)
    assignment.update_demands(d)
