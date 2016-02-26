#!/usr/bin/env python3

"""
Module that implements the Reid/Daid/Hurley algorithm for community finding.
"""

import networkx
from ..utilities.log_utils import create_null_logger, create_default_logger
from collections import defaultdict

__all__ = ["reid_daid_hurley"]


def find_communities(graph: networkx.Graph, logger=None) -> list:
    """

    :param graph: a Graph instance from networkx
    :type graph: networkx.Graph

    :param logger: optional logger. A default null one will be created if none is provided.
    :type logger: (None|logging.Logger)

    This function is a wrapper around the networkX methods to find
    cliques and communities inside a graph.
    The method takes as input a precomputed graph and returns
    two lists:
        - cliques
        - communities
    """
    if logger is None:
        logger = create_default_logger("comms")

    # graph = deepcopy(graph)
    # logger.debug("Creating the cliques for %s", logger.name)
    # # cliques = []
    # # counter = 0
    # # communities = []

    # nx_comms = [frozenset(x) for x in networkx.k_clique_communities(graph, 2, cliques)]
    # rdh_comms = reid_daid_hurley(graph, 2, cliques)
    #
    # for comm in rdh_comms:
    #     if len(comm) == 1:
    #         continue
    #     if not any([comm == _ for _ in nx_comms]):
    #         logger.error("Discrepant communities for %s;\n%s\n%s",
    #                      logger.name, nx_comms, rdh_comms)
    #         raise AssertionError

    logger.debug("Creating the communities for %s", logger.name)
    communities = set(frozenset(comm) for comm in networkx.connected_components(graph))

    # communities = set(frozenset(x) for x in cliques if len(x) == 1)
    # for comm in reid_daid_hurley(graph, 2, cliques=cliques, logger=logger):
    #     communities.add(comm)

    logger.debug("Communities for %s:\n\t\t%s", logger.name, "\n\t\t".join(
        [str(_) for _ in communities]))
    return communities


def define_graph(objects: dict, inters, **kwargs) -> networkx.Graph:
    """
    :param objects: a dictionary of objects to be grouped into a graph
    :type objects: dict

    :param inters: the intersecting function to be used to define the graph
    :type inters: callable

    :param kwargs: optional arguments to be passed to the inters function
    :type kwargs: dict

    This function will compute the graph which will later be used by find_communities.
    The method takes as mandatory inputs the following:
        - "objects" a dictionary of objects that form the graph
        - "inters" a function/method that determines whether two objects are connected or not.

    It will then return a graph.
    The method accepts also kwargs that can be passed to the inters function.
    WARNING: the kwargs option is really stupid and does not check
    for correctness of the arguments!
    """

    graph = networkx.Graph()

    # As we are using intern for transcripts, this should prevent
    # memory usage to increase too much
    graph.add_nodes_from(objects.keys())

    for obj in objects:
        for other_obj in iter(x for x in objects if x != obj):
            if inters(objects[obj], objects[other_obj], **kwargs):
                # Connections are not directional
                graph.add_edge(*tuple(sorted([obj, other_obj])))

    return graph


def overlap(first_interval: tuple([int, int]),
            second_interval: tuple([int, int]), flank=0) -> int:

    """
    :param first_interval: a tuple of integers
    :type first_interval: (int,int)

    :param second_interval: a tuple of integers
    :type second_interval: (int,int | intervaltree.Interval)

    :param flank: an optional extending parameter to check for neighbours
    :type flank: int

    This static method returns the overlap between two intervals.

    Values<=0 indicate no overlap.

    The optional "flank" argument (default 0) allows to expand a locus
    upstream and downstream.
    As a static method, it can be used also outside of any instance -
    "abstractlocus.overlap()" will function.
    Input: two 2-tuples of integers.
    """

    first_interval = sorted(first_interval[:2])
    second_interval = sorted(second_interval[:2])

    left_boundary = max(first_interval[0] - flank, second_interval[0] - flank)
    right_boundary = min(first_interval[1] + flank, second_interval[1] + flank)

    return right_boundary - left_boundary

def find_cliques(graph: networkx.Graph, logger=None) -> (networkx.Graph, list):
    """

    :param graph: graph to which it is necessary to call the cliques for.

    :param logger: optional logger for the function

    Wrapper for the BronKerbosch algorithm, which returns the maximal cliques in the graph.
    It is the new interface for the BronKerbosch function, which is not called directly
    from outside this class any longer.
    The "inters" keyword provides the function used to determine
    whether two vertices are connected or not in the graph.
    """

    if logger is None:
        logger = create_default_logger("cliques")

    logger.debug("Creating cliques for %s", logger.name)
    cliques = [frozenset(x) for x in networkx.find_cliques_recursive(graph)]
    logger.debug("Created %d cliques for %s", len(cliques), logger.name)

    return cliques

def reid_daid_hurley(graph, k, cliques=None, logger=None):

    """
    Implementation of the Reid-Daid-Hurley algorithm for clique percolation
    published in http://arxiv.org/pdf/1205.0038.pdf

    :param graph:
    :param k:
    :param cliques:
    :param logger: optional logger for the function
    :return:
    """

    if k < 2:
        raise networkx.NetworkXError("k=%d, k must be greater than 1." % k)
    if cliques is None:
        cliques = [frozenset(x) for x in networkx.find_cliques_recursive(graph)]

    if logger is None:
        logger = create_null_logger("null")

    nodes_to_clique_dict = defaultdict(set)
    # Create the dictionary that links each node to its clique
    logger.debug("Creating the node dictionary")
    cliques = [_ for _ in cliques if len(_) >= k]
    for clique in cliques:
        for node in clique:
            nodes_to_clique_dict[node].add(clique)

    if len(nodes_to_clique_dict) > 100 or len(cliques) > 500:
        logger.debug("Complex locus at %s, with %d nodes and %d cliques with length >= %d",
                     logger.name, len(nodes_to_clique_dict), len(cliques), k)

    current_component = 0

    logger.debug("Starting to explore the clique graph")
    cliques_to_components_dict = dict()
    counter = 0
    for clique in cliques:
        # visited = set()
        counter += 1
        logger.debug("Exploring clique %d out of %d", counter, len(cliques))
        if clique not in cliques_to_components_dict:
            current_component += 1
            cliques_to_components_dict[clique] = current_component
            frontier = set()
            frontier.add(clique)
            cycle = 0
            while len(frontier) > 0:
                current_clique = frontier.pop()
                # if current_clique in visited_cliques:
                #     continue
                cycle += 1
                logger.debug("Cycle %d for clique %d with %d nodes",
                             cycle,
                             counter,
                             len(current_clique))

                for neighbour in _get_unvisited_neighbours(current_clique, nodes_to_clique_dict):
                    if len(frozenset.intersection(current_clique, neighbour)) >= (k-1):
                        cliques_to_components_dict[neighbour] = current_component
                        frontier.add(neighbour)
                        for node in neighbour:
                            nodes_to_clique_dict[node].remove(neighbour)

                logger.debug("Found %d neighbours of clique %d in cycle %d",
                             len(frontier), counter, cycle)

    logger.debug("Finished exploring the clique graph")
    communities = dict()
    for clique in cliques_to_components_dict:
        if cliques_to_components_dict[clique] not in communities:
            communities[cliques_to_components_dict[clique]] = set()
        communities[cliques_to_components_dict[clique]].update(set(clique))

    logger.debug("Reporting the results")
    return [frozenset(x) for x in communities.values()]


def _get_unvisited_neighbours(current_clique, nodes_to_clique_dict):

    """

    :param current_clique:
    :param nodes_to_clique_dict:
    :return:
    """

    neighbours = set()
    for node in current_clique:
        neighbours.update(nodes_to_clique_dict[node])
    return frozenset(neighbours - {current_clique})
