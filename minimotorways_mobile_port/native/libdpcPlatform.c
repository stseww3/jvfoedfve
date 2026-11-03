/*
 * libdpcPlatform.c — Clean-room C99 replacement for dpcPlatform.dll
 * Targets Android ARM64 (libdpcPlatform.so) and desktop host testing.
 *
 * Implements all exported functions called by Mini Motorways:
 *   1. DllUtilities:
 *      - EmptyFunction
 *   2. ExternPathfinding (20 exports):
 *      - Setup, Clear, PauseUpdate, ResumeUpdate
 *      - AddNode, MergeNodes, AddEdge, RemoveEdge, ChangeEdgeCost
 *      - GetPathCost, GetPathNextEdge, GetPathNextNode, GetEdgeCost
 *      - GetNeighbourCount, GetNeighbour, IsNodeEndpoint, MakeNodeEndpoint
 *      - AreNodesConnected, GetNoPathCostConstant, DebugPrintPathfindingGraphs
 *   3. VehicleMovementProcess:
 *      - CalculateAcceleration (Fix64 Q32.32 Intelligent Driver Model)
 *   4. G-Audio DSP:
 *      - GainMixToInterlaced, ResampleCopyFromInt16, LFOProcessChunk
 *   5. AnimatedGifEncoder:
 *      - AllocateBuffer, FreeBuffer, QuantizeImage
 *   6. MultiDisplayCapabilitiesBridge:
 *      - GetDisplayCount, GetActiveDisplayIndex, SetActiveDisplay
 *   7. Apple / iCloud / GameCenter stubs (so no EntryPointNotFoundException can occur)
 */

#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdio.h>

#if defined(_WIN32)
#define DPC_EXPORT __declspec(dllexport)
#else
#define DPC_EXPORT __attribute__((visibility("default")))
#endif

typedef void (*ReportErrorFn)(const char*);

#define NO_PATH_COST 0x3fffffff
#define MAX_PATHFINDERS 32

typedef struct {
    int32_t edge_id;
    int32_t from_node;
    int32_t to_node;
    int32_t cost;
    bool active;
} PfEdge;

typedef struct {
    int32_t node_id;
    bool active;
    bool is_endpoint;
    int32_t* out_edges;
    int32_t out_count;
    int32_t out_cap;
    int32_t* in_edges;
    int32_t in_count;
    int32_t in_cap;
} PfNode;

typedef struct {
    bool active;
    bool paused;
    bool dirty;
    PfNode* nodes;
    int32_t node_count;
    int32_t node_cap;
    PfEdge* edges;
    int32_t edge_count;
    int32_t edge_cap;
    /* All-pairs-to-endpoints shortest path cache:
     * Indexed by [endpoint_slot * node_cap + from_node] */
    int32_t* ep_nodes;
    int32_t ep_count;
    int32_t ep_cap;
    int32_t* dist_table;
    int32_t* next_edge_table;
    int32_t* next_node_table;
    int32_t table_node_cap;
    int32_t table_ep_cap;
} PathfinderInstance;

static PathfinderInstance g_pathfinders[MAX_PATHFINDERS];
static int32_t g_next_pf_id = 0;

static void vec_push_int(int32_t** arr, int32_t* count, int32_t* cap, int32_t val) {
    for (int32_t i = 0; i < *count; i++) {
        if ((*arr)[i] == val) return;
    }
    if (*count >= *cap) {
        int32_t new_cap = (*cap == 0) ? 8 : (*cap * 2);
        int32_t* next = (int32_t*)realloc(*arr, (size_t)new_cap * sizeof(int32_t));
        if (!next) return;
        *arr = next;
        *cap = new_cap;
    }
    (*arr)[(*count)++] = val;
}

static void vec_remove_int(int32_t* arr, int32_t* count, int32_t val) {
    for (int32_t i = 0; i < *count; i++) {
        if (arr[i] == val) {
            for (int32_t j = i; j + 1 < *count; j++) {
                arr[j] = arr[j + 1];
            }
            (*count)--;
            return;
        }
    }
}

static PathfinderInstance* get_pf(int32_t pf_id, ReportErrorFn report_error) {
    if (pf_id < 0 || pf_id >= MAX_PATHFINDERS || !g_pathfinders[pf_id].active) {
        if (report_error) report_error("[ERROR!] Unrecognised pathfinder ID");
        return NULL;
    }
    return &g_pathfinders[pf_id];
}

static void recompute_paths(PathfinderInstance* pf) {
    if (!pf->dirty || pf->paused) return;

    int32_t n = pf->node_count;
    if (n <= 0) {
        pf->dirty = false;
        return;
    }

    pf->ep_count = 0;
    for (int32_t u = 0; u < n; u++) {
        if (pf->nodes[u].active && pf->nodes[u].is_endpoint) {
            vec_push_int(&pf->ep_nodes, &pf->ep_count, &pf->ep_cap, u);
        }
    }

    int32_t ep_cnt = pf->ep_count;
    if (ep_cnt == 0) {
        pf->dirty = false;
        return;
    }

    if (n > pf->table_node_cap || ep_cnt > pf->table_ep_cap) {
        int32_t new_ncap = n > pf->table_node_cap ? (n * 2 + 16) : pf->table_node_cap;
        int32_t new_ecap = ep_cnt > pf->table_ep_cap ? (ep_cnt * 2 + 8) : pf->table_ep_cap;
        size_t total = (size_t)new_ncap * (size_t)new_ecap;
        free(pf->dist_table);
        free(pf->next_edge_table);
        free(pf->next_node_table);
        pf->dist_table = (int32_t*)malloc(total * sizeof(int32_t));
        pf->next_edge_table = (int32_t*)malloc(total * sizeof(int32_t));
        pf->next_node_table = (int32_t*)malloc(total * sizeof(int32_t));
        pf->table_node_cap = new_ncap;
        pf->table_ep_cap = new_ecap;
    }

    int32_t stride = pf->table_node_cap;
    int32_t* visited = (int32_t*)malloc((size_t)n * sizeof(int32_t));
    if (!visited) return;

    /* Run reverse Dijkstra from each endpoint node */
    for (int32_t ei = 0; ei < ep_cnt; ei++) {
        int32_t target = pf->ep_nodes[ei];
        int32_t* dist = pf->dist_table + (size_t)ei * (size_t)stride;
        int32_t* next_edge = pf->next_edge_table + (size_t)ei * (size_t)stride;
        int32_t* next_node = pf->next_node_table + (size_t)ei * (size_t)stride;

        for (int32_t u = 0; u < n; u++) {
            dist[u] = NO_PATH_COST;
            next_edge[u] = -1;
            next_node[u] = -1;
            visited[u] = 0;
        }
        dist[target] = 0;

        for (int32_t step = 0; step < n; step++) {
            int32_t best_u = -1;
            int32_t best_d = NO_PATH_COST;
            for (int32_t u = 0; u < n; u++) {
                if (!visited[u] && dist[u] < best_d) {
                    best_d = dist[u];
                    best_u = u;
                }
            }
            if (best_u < 0) break;
            visited[best_u] = 1;

            PfNode* node_u = &pf->nodes[best_u];
            for (int32_t i = 0; i < node_u->in_count; i++) {
                int32_t e_id = node_u->in_edges[i];
                PfEdge* e = &pf->edges[e_id];
                if (!e->active) continue;
                int32_t pred = e->from_node;
                if (!pf->nodes[pred].active) continue;
                int64_t cand = (int64_t)best_d + (int64_t)e->cost;
                if (cand < dist[pred]) {
                    dist[pred] = (int32_t)cand;
                    next_edge[pred] = e_id;
                    next_node[pred] = best_u;
                }
            }
        }
    }

    free(visited);
    pf->dirty = false;
}

static int32_t find_ep_slot(PathfinderInstance* pf, int32_t endpoint_node) {
    recompute_paths(pf);
    for (int32_t i = 0; i < pf->ep_count; i++) {
        if (pf->ep_nodes[i] == endpoint_node) return i;
    }
    return -1;
}

DPC_EXPORT int32_t EmptyFunction(void) {
    return 0;
}

DPC_EXPORT int32_t GetNoPathCostConstant(void) {
    return NO_PATH_COST;
}

DPC_EXPORT int32_t Setup(void) {
    for (int32_t i = 0; i < MAX_PATHFINDERS; i++) {
        int32_t idx = (g_next_pf_id + i) % MAX_PATHFINDERS;
        if (!g_pathfinders[idx].active) {
            memset(&g_pathfinders[idx], 0, sizeof(PathfinderInstance));
            g_pathfinders[idx].active = true;
            g_next_pf_id = (idx + 1) % MAX_PATHFINDERS;
            return idx;
        }
    }
    int32_t idx = 0;
    g_pathfinders[idx].active = true;
    g_pathfinders[idx].node_count = 0;
    g_pathfinders[idx].edge_count = 0;
    g_pathfinders[idx].ep_count = 0;
    g_pathfinders[idx].paused = false;
    g_pathfinders[idx].dirty = false;
    return idx;
}

DPC_EXPORT int32_t Clear(int32_t pf_id, ReportErrorFn report_error) {
    PathfinderInstance* pf = get_pf(pf_id, report_error);
    if (!pf) return -1;
    for (int32_t i = 0; i < pf->node_count; i++) {
        free(pf->nodes[i].out_edges);
        free(pf->nodes[i].in_edges);
        pf->nodes[i].out_edges = NULL;
        pf->nodes[i].in_edges = NULL;
        pf->nodes[i].out_count = 0;
        pf->nodes[i].out_cap = 0;
        pf->nodes[i].in_count = 0;
        pf->nodes[i].in_cap = 0;
        pf->nodes[i].active = false;
        pf->nodes[i].is_endpoint = false;
    }
    pf->node_count = 0;
    pf->edge_count = 0;
    pf->ep_count = 0;
    pf->paused = false;
    pf->dirty = false;
    return 0;
}

DPC_EXPORT int32_t PauseUpdate(int32_t pf_id, ReportErrorFn report_error) {
    PathfinderInstance* pf = get_pf(pf_id, report_error);
    if (!pf) return -1;
    pf->paused = true;
    return 0;
}

DPC_EXPORT int32_t ResumeUpdate(int32_t pf_id, ReportErrorFn report_error) {
    PathfinderInstance* pf = get_pf(pf_id, report_error);
    if (!pf) return -1;
    pf->paused = false;
    recompute_paths(pf);
    return 0;
}

DPC_EXPORT int32_t AddNode(int32_t pf_id, bool is_endpoint, ReportErrorFn report_error) {
    PathfinderInstance* pf = get_pf(pf_id, report_error);
    if (!pf) return -1;
    if (pf->node_count >= pf->node_cap) {
        int32_t new_cap = (pf->node_cap == 0) ? 64 : (pf->node_cap * 2);
        PfNode* next = (PfNode*)realloc(pf->nodes, (size_t)new_cap * sizeof(PfNode));
        if (!next) return -1;
        pf->nodes = next;
        pf->node_cap = new_cap;
    }
    int32_t id = pf->node_count++;
    PfNode* node = &pf->nodes[id];
    memset(node, 0, sizeof(PfNode));
    node->node_id = id;
    node->active = true;
    node->is_endpoint = is_endpoint;
    if (is_endpoint) {
        pf->dirty = true;
        recompute_paths(pf);
    }
    return id;
}

static int32_t find_active_edge(PathfinderInstance* pf, int32_t u, int32_t v) {
    if (u < 0 || u >= pf->node_count || !pf->nodes[u].active) return -1;
    PfNode* nu = &pf->nodes[u];
    for (int32_t i = 0; i < nu->out_count; i++) {
        int32_t eid = nu->out_edges[i];
        if (pf->edges[eid].active && pf->edges[eid].to_node == v) {
            return eid;
        }
    }
    return -1;
}

DPC_EXPORT int32_t AddEdge(int32_t pf_id, int32_t u, int32_t v, int32_t cost, ReportErrorFn report_error) {
    PathfinderInstance* pf = get_pf(pf_id, report_error);
    if (!pf) return -1;
    if (u < 0 || u >= pf->node_count || !pf->nodes[u].active ||
        v < 0 || v >= pf->node_count || !pf->nodes[v].active ||
        u == v || cost <= 0) {
        return -1;
    }
    int32_t existing = find_active_edge(pf, u, v);
    if (existing >= 0) {
        pf->edges[existing].cost = cost;
        pf->dirty = true;
        recompute_paths(pf);
        return existing;
    }
    if (pf->edge_count >= pf->edge_cap) {
        int32_t new_cap = (pf->edge_cap == 0) ? 128 : (pf->edge_cap * 2);
        PfEdge* next = (PfEdge*)realloc(pf->edges, (size_t)new_cap * sizeof(PfEdge));
        if (!next) return -1;
        pf->edges = next;
        pf->edge_cap = new_cap;
    }
    int32_t eid = pf->edge_count++;
    PfEdge* e = &pf->edges[eid];
    e->edge_id = eid;
    e->from_node = u;
    e->to_node = v;
    e->cost = cost;
    e->active = true;

    vec_push_int(&pf->nodes[u].out_edges, &pf->nodes[u].out_count, &pf->nodes[u].out_cap, eid);
    vec_push_int(&pf->nodes[v].in_edges, &pf->nodes[v].in_count, &pf->nodes[v].in_cap, eid);

    pf->dirty = true;
    recompute_paths(pf);
    return eid;
}

DPC_EXPORT bool RemoveEdge(int32_t pf_id, int32_t u, int32_t v, ReportErrorFn report_error) {
    PathfinderInstance* pf = get_pf(pf_id, report_error);
    if (!pf) return false;
    int32_t eid = find_active_edge(pf, u, v);
    if (eid < 0) return false;
    pf->edges[eid].active = false;
    vec_remove_int(pf->nodes[u].out_edges, &pf->nodes[u].out_count, eid);
    vec_remove_int(pf->nodes[v].in_edges, &pf->nodes[v].in_count, eid);
    pf->dirty = true;
    recompute_paths(pf);
    return true;
}

DPC_EXPORT bool ChangeEdgeCost(int32_t pf_id, int32_t u, int32_t v, int32_t new_cost, ReportErrorFn report_error) {
    PathfinderInstance* pf = get_pf(pf_id, report_error);
    if (!pf || new_cost <= 0) return false;
    int32_t eid = find_active_edge(pf, u, v);
    if (eid < 0) return false;
    if (pf->edges[eid].cost != new_cost) {
        pf->edges[eid].cost = new_cost;
        pf->dirty = true;
        recompute_paths(pf);
    }
    return true;
}

DPC_EXPORT bool MergeNodes(int32_t pf_id, int32_t into_node, int32_t from_node, ReportErrorFn report_error) {
    PathfinderInstance* pf = get_pf(pf_id, report_error);
    if (!pf) return false;
    if (into_node == from_node ||
        into_node < 0 || into_node >= pf->node_count || !pf->nodes[into_node].active ||
        from_node < 0 || from_node >= pf->node_count || !pf->nodes[from_node].active) {
        return false;
    }

    PfNode* dst = &pf->nodes[into_node];
    PfNode* src = &pf->nodes[from_node];

    if (src->is_endpoint) {
        dst->is_endpoint = true;
    }

    /* Redirect outgoing edges from from_node -> into_node */
    for (int32_t i = 0; i < src->out_count; i++) {
        int32_t eid = src->out_edges[i];
        PfEdge* e = &pf->edges[eid];
        if (!e->active) continue;
        if (e->to_node == into_node) {
            e->active = false;
            vec_remove_int(dst->in_edges, &dst->in_count, eid);
            continue;
        }
        int32_t dup = find_active_edge(pf, into_node, e->to_node);
        if (dup >= 0) {
            e->active = false;
            vec_remove_int(pf->nodes[e->to_node].in_edges, &pf->nodes[e->to_node].in_count, eid);
        } else {
            e->from_node = into_node;
            vec_push_int(&dst->out_edges, &dst->out_count, &dst->out_cap, eid);
        }
    }

    /* Redirect incoming edges into from_node -> into_node */
    for (int32_t i = 0; i < src->in_count; i++) {
        int32_t eid = src->in_edges[i];
        PfEdge* e = &pf->edges[eid];
        if (!e->active) continue;
        if (e->from_node == into_node) {
            e->active = false;
            vec_remove_int(dst->out_edges, &dst->out_count, eid);
            continue;
        }
        int32_t dup = find_active_edge(pf, e->from_node, into_node);
        if (dup >= 0) {
            e->active = false;
            vec_remove_int(pf->nodes[e->from_node].out_edges, &pf->nodes[e->from_node].out_count, eid);
        } else {
            e->to_node = into_node;
            vec_push_int(&dst->in_edges, &dst->in_count, &dst->in_cap, eid);
        }
    }

    src->out_count = 0;
    src->in_count = 0;
    src->active = false;
    src->is_endpoint = false;

    pf->dirty = true;
    recompute_paths(pf);
    return true;
}

DPC_EXPORT int32_t GetPathCost(int32_t pf_id, int32_t from_node, int32_t endpoint_node, ReportErrorFn report_error) {
    PathfinderInstance* pf = get_pf(pf_id, report_error);
    if (!pf) return NO_PATH_COST;
    if (from_node < 0 || from_node >= pf->node_count || !pf->nodes[from_node].active) return NO_PATH_COST;
    int32_t slot = find_ep_slot(pf, endpoint_node);
    if (slot < 0) return NO_PATH_COST;
    return pf->dist_table[(size_t)slot * (size_t)pf->table_node_cap + (size_t)from_node];
}

DPC_EXPORT int32_t GetPathNextEdge(int32_t pf_id, int32_t from_node, int32_t endpoint_node, ReportErrorFn report_error) {
    PathfinderInstance* pf = get_pf(pf_id, report_error);
    if (!pf) return -1;
    if (from_node < 0 || from_node >= pf->node_count || !pf->nodes[from_node].active) return -1;
    int32_t slot = find_ep_slot(pf, endpoint_node);
    if (slot < 0) return -1;
    return pf->next_edge_table[(size_t)slot * (size_t)pf->table_node_cap + (size_t)from_node];
}

DPC_EXPORT int32_t GetPathNextNode(int32_t pf_id, int32_t from_node, int32_t endpoint_node, ReportErrorFn report_error) {
    PathfinderInstance* pf = get_pf(pf_id, report_error);
    if (!pf) return -1;
    if (from_node < 0 || from_node >= pf->node_count || !pf->nodes[from_node].active) return -1;
    int32_t slot = find_ep_slot(pf, endpoint_node);
    if (slot < 0) return -1;
    return pf->next_node_table[(size_t)slot * (size_t)pf->table_node_cap + (size_t)from_node];
}

DPC_EXPORT int32_t GetEdgeCost(int32_t pf_id, int32_t from_node, int32_t to_node, ReportErrorFn report_error) {
    PathfinderInstance* pf = get_pf(pf_id, report_error);
    if (!pf) return -1;
    int32_t eid = find_active_edge(pf, from_node, to_node);
    return (eid >= 0) ? pf->edges[eid].cost : -1;
}

DPC_EXPORT int32_t GetNeighbourCount(int32_t pf_id, int32_t from_node, ReportErrorFn report_error) {
    PathfinderInstance* pf = get_pf(pf_id, report_error);
    if (!pf || from_node < 0 || from_node >= pf->node_count || !pf->nodes[from_node].active) return 0;
    return pf->nodes[from_node].out_count;
}

DPC_EXPORT int32_t GetNeighbour(int32_t pf_id, int32_t from_node, int32_t neighbour_index, ReportErrorFn report_error) {
    PathfinderInstance* pf = get_pf(pf_id, report_error);
    if (!pf || from_node < 0 || from_node >= pf->node_count || !pf->nodes[from_node].active) return -1;
    PfNode* n = &pf->nodes[from_node];
    if (neighbour_index < 0 || neighbour_index >= n->out_count) return -1;
    int32_t eid = n->out_edges[neighbour_index];
    return pf->edges[eid].to_node;
}

DPC_EXPORT bool IsNodeEndpoint(int32_t pf_id, int32_t node_id, ReportErrorFn report_error) {
    PathfinderInstance* pf = get_pf(pf_id, report_error);
    if (!pf || node_id < 0 || node_id >= pf->node_count || !pf->nodes[node_id].active) return false;
    return pf->nodes[node_id].is_endpoint;
}

DPC_EXPORT void MakeNodeEndpoint(int32_t pf_id, int32_t node_id, ReportErrorFn report_error) {
    PathfinderInstance* pf = get_pf(pf_id, report_error);
    if (!pf || node_id < 0 || node_id >= pf->node_count || !pf->nodes[node_id].active) return;
    if (!pf->nodes[node_id].is_endpoint) {
        pf->nodes[node_id].is_endpoint = true;
        pf->dirty = true;
        recompute_paths(pf);
    }
}

DPC_EXPORT bool AreNodesConnected(int32_t pf_id, int32_t node1, int32_t node2, int32_t cost_upper_limit, ReportErrorFn report_error) {
    PathfinderInstance* pf = get_pf(pf_id, report_error);
    if (!pf) return false;
    if (node1 < 0 || node1 >= pf->node_count || !pf->nodes[node1].active ||
        node2 < 0 || node2 >= pf->node_count || !pf->nodes[node2].active) {
        return false;
    }
    if (node1 == node2) return true;

    recompute_paths(pf);

    /* Fast path: if node2 is an endpoint, check dist(node1 -> node2) < cost_upper_limit */
    int32_t slot2 = find_ep_slot(pf, node2);
    if (slot2 >= 0) {
        int32_t c = pf->dist_table[(size_t)slot2 * (size_t)pf->table_node_cap + (size_t)node1];
        if (c < cost_upper_limit) return true;
    }

    /* Also check if both node1 and node2 can reach a common endpoint within cost_upper_limit */
    for (int32_t ei = 0; ei < pf->ep_count; ei++) {
        int32_t c1 = pf->dist_table[(size_t)ei * (size_t)pf->table_node_cap + (size_t)node1];
        int32_t c2 = pf->dist_table[(size_t)ei * (size_t)pf->table_node_cap + (size_t)node2];
        if (c1 < cost_upper_limit && c2 < cost_upper_limit) {
            return true;
        }
    }
    return false;
}

DPC_EXPORT const char* DebugPrintPathfindingGraphs(ReportErrorFn report_error) {
    (void)report_error;
    return "PathfindingGraphs(Android native)";
}

/* =========================================================================
 * VehicleMovementProcess: CalculateAcceleration (Fix64 Q32.32)
 * Matches VehicleMovementProcess.ReferenceCalculateAcceleration
 * ========================================================================= */
DPC_EXPORT int64_t CalculateAcceleration(
    int64_t currentGapRaw,
    int64_t currentSpeedRaw,
    int64_t leadingSpeedRaw,
    int64_t leadingAccelerationRaw,
    int64_t desiredSpeedRaw,
    int64_t maximumAccelerationRaw,
    int64_t accelerationExponentRaw,
    int64_t maximumDecelerationRaw,
    int64_t decelerationExponentRaw)
{
    const double scale = 4294967296.0; /* 2^32 */
    const double vehicleLength = 2791728742.0 / scale; /* ~0.65 */
    const double minimumGap = 429496729.0 / scale;     /* ~0.10 */
    const double desiredTimeGap = 1.0;
    const double coolnessFactor = 858993459.0 / scale; /* ~0.20 */
    const double oneEMinus3 = 429496.0 / scale;
    const double oneEMinus5 = 4294.0 / scale;

    double currentGap = (double)currentGapRaw / scale;
    double currentSpeed = (double)currentSpeedRaw / scale;
    double leadingSpeed = (double)leadingSpeedRaw / scale;
    double leadingAcceleration = (double)leadingAccelerationRaw / scale;
    double desiredSpeed = (double)desiredSpeedRaw / scale;
    double maximumAcceleration = (double)maximumAccelerationRaw / scale;
    double accelerationExponent = (double)accelerationExponentRaw / scale;
    double maximumDeceleration = (double)maximumDecelerationRaw / scale;
    double decelerationExponent = (double)decelerationExponentRaw / scale;

    if (desiredSpeed < oneEMinus5) {
        return 0;
    }

    double gap = currentGap - vehicleLength;
    if (gap < minimumGap) gap = minimumGap;

    double speedDelta = currentSpeed - leadingSpeed;
    double freeAcc;
    if (currentSpeed <= desiredSpeed) {
        double ratio = (desiredSpeed > 0.0) ? (currentSpeed / desiredSpeed) : 0.0;
        freeAcc = maximumAcceleration * (1.0 - pow(fabs(ratio), accelerationExponent));
    } else {
        double ratio = (currentSpeed > 0.0) ? (desiredSpeed / currentSpeed) : 0.0;
        double exp = (maximumDeceleration > 0.0) ? (maximumAcceleration * decelerationExponent / maximumDeceleration) : 1.0;
        freeAcc = -maximumDeceleration * (1.0 - pow(fabs(ratio), exp));
    }

    double sqrtAccDec = sqrt(fabs(maximumAcceleration * maximumDeceleration));
    double term = currentSpeed * desiredTimeGap + (sqrtAccDec > 0.0 ? (0.5 * currentSpeed * speedDelta / sqrtAccDec) : 0.0);
    if (term < 0.0) term = 0.0;
    double z = (minimumGap + term) / gap;
    double intAcc = maximumAcceleration * (1.0 - z * z);

    double idmAcc;
    if (currentSpeed <= desiredSpeed) {
        if (z >= 1.0) {
            idmAcc = intAcc;
        } else {
            double denom = freeAcc > oneEMinus3 ? freeAcc : oneEMinus3;
            idmAcc = freeAcc * (1.0 - pow(fabs(z), 2.0 * maximumAcceleration / denom));
        }
    } else {
        idmAcc = (z >= 1.0) ? (freeAcc + intAcc) : freeAcc;
    }

    double approachSign = (speedDelta >= 0.0) ? 1.0 : 0.0;
    double twoGapLeadAcc = 2.0 * gap * leadingAcceleration;
    if (fabs(twoGapLeadAcc) < 1e-12) {
        twoGapLeadAcc = oneEMinus5;
    }

    double cAcc;
    if (leadingSpeed * speedDelta < -twoGapLeadAcc) {
        double denom = leadingSpeed * leadingSpeed - twoGapLeadAcc;
        cAcc = (fabs(denom) > 1e-12) ? (currentSpeed * currentSpeed * leadingAcceleration / denom) : 0.0;
    } else {
        cAcc = leadingAcceleration - (speedDelta * speedDelta * approachSign) / (2.0 * gap);
    }
    if (cAcc > maximumAcceleration) cAcc = maximumAcceleration;

    double finalAcc;
    if (idmAcc >= cAcc) {
        finalAcc = idmAcc;
    } else {
        finalAcc = (1.0 - coolnessFactor) * idmAcc
                 + coolnessFactor * (cAcc + maximumDeceleration * tanh((idmAcc - cAcc) / maximumDeceleration));
    }

    if (finalAcc < -maximumDeceleration) {
        finalAcc = -maximumDeceleration;
    }

    double scaled = finalAcc * scale;
    if (scaled >= (double)INT64_MAX) return INT64_MAX;
    if (scaled <= (double)INT64_MIN) return INT64_MIN;
    return (int64_t)llround(scaled);
}

/* =========================================================================
 * G-Audio DSP functions:
 *   - GainMixToInterlaced
 *   - ResampleCopyFromInt16
 *   - LFOProcessChunk
 * ========================================================================= */
DPC_EXPORT void GainMixToInterlaced(
    float* destinationArray,
    int32_t destinationOffset,
    int32_t channelCount,
    const float* sourceArray,
    int32_t sourceIndex,
    int32_t length,
    float gain)
{
    if (!destinationArray || !sourceArray || channelCount <= 0) return;
    int32_t dst = destinationOffset;
    for (int32_t src = sourceIndex; src < length; src++) {
        destinationArray[dst] += sourceArray[src] * gain;
        dst += channelCount;
    }
}

DPC_EXPORT float ResampleCopyFromInt16(
    const int16_t* sourceArray,
    int32_t sourceLength,
    int32_t sourceOffset,
    int32_t maxSourceIndex,
    bool sourceLoops,
    float trueInterpolatedIndex,
    float* parentArray,
    int32_t targetLength,
    int32_t targetOffset,
    float resamplingFactor)
{
    const float int16ToFloat = 1.0f / 32768.0f;
    if (!sourceArray || !parentArray) return trueInterpolatedIndex;
    for (int32_t num = targetOffset; num < targetLength; num++) {
        int32_t idx0 = (int32_t)trueInterpolatedIndex;
        if (idx0 > maxSourceIndex) idx0 = maxSourceIndex;
        int32_t idx1 = idx0 + 1;
        if (idx1 >= sourceOffset + sourceLength) {
            idx1 = sourceLoops ? (idx1 - sourceLength) : idx0;
        }
        float frac = trueInterpolatedIndex - (float)idx0;
        float s0 = (float)sourceArray[idx0] * (1.0f - frac);
        parentArray[num] = (s0 + (float)sourceArray[idx1] * frac) * int16ToFloat;
        trueInterpolatedIndex += resamplingFactor;
    }
    return trueInterpolatedIndex;
}

DPC_EXPORT float LFOProcessChunk(
    float* data,
    int32_t sourceIndex,
    int32_t length,
    int32_t stride,
    float phase,
    float phaseIncrement,
    float strength)
{
    const float twoPi = 6.283185307179586f;
    if (!data || stride <= 0) return phase;
    int32_t end = sourceIndex + length;
    for (int32_t i = sourceIndex; i < end; i += stride) {
        float mod = (sinf(phase) + 1.0f) * 0.5f;
        mod = mod * strength + (1.0f - strength);
        phase += phaseIncrement;
        if (phase > twoPi) {
            phase -= twoPi;
        }
        data[i] *= mod;
    }
    return phase;
}

/* =========================================================================
 * Multi-display & GIF encoder exports
 * ========================================================================= */
DPC_EXPORT int32_t GetDisplayCount(void) {
    return 1;
}

DPC_EXPORT int32_t GetActiveDisplayIndex(void) {
    return 0;
}

DPC_EXPORT bool SetActiveDisplay(int32_t displayIndex) {
    return displayIndex == 0;
}

static int32_t g_gif_w = 0;
static int32_t g_gif_h = 0;

DPC_EXPORT void AllocateBuffer(int32_t imageWidth, int32_t imageHeight) {
    g_gif_w = imageWidth;
    g_gif_h = imageHeight;
}

DPC_EXPORT void FreeBuffer(void) {
    g_gif_w = 0;
    g_gif_h = 0;
}

DPC_EXPORT void QuantizeImage(uint8_t* indexedPixels, uint8_t* colorMap, const uint8_t* pixels, bool isFirstImage) {
    int32_t count = g_gif_w * g_gif_h;
    if (!indexedPixels || !colorMap || !pixels || count <= 0) return;
    if (isFirstImage) {
        /* 3-3-2 uniform palette */
        for (int i = 0; i < 256; i++) {
            colorMap[i * 3 + 0] = (uint8_t)(((i >> 5) & 7) * 255 / 7);
            colorMap[i * 3 + 1] = (uint8_t)(((i >> 2) & 7) * 255 / 7);
            colorMap[i * 3 + 2] = (uint8_t)((i & 3) * 255 / 3);
        }
    }
    for (int32_t p = 0; p < count; p++) {
        uint8_t r = pixels[p * 3 + 0] >> 5;
        uint8_t g = pixels[p * 3 + 1] >> 5;
        uint8_t b = pixels[p * 3 + 2] >> 6;
        indexedPixels[p] = (uint8_t)((r << 5) | (g << 2) | b);
    }
}

/* =========================================================================
 * Apple Reachability / iCloud / GameCenter safe stubs
 * ========================================================================= */
DPC_EXPORT void StartCheckingReachability(void* handler) { (void)handler; }
DPC_EXPORT bool IsReachable(void) { return true; }
DPC_EXPORT void iCloudAttemptLogin(void* a, void* b, void* c, void* d, void* e, void* f, void* g, const char* h, const char* i) {
    (void)a; (void)b; (void)c; (void)d; (void)e; (void)f; (void)g; (void)h; (void)i;
}
DPC_EXPORT int64_t iCloudGetFunctionPointerToNotificationCallback(void) { return 0; }
DPC_EXPORT bool iCloudWriteFile(const char* f, const void* d, int32_t l) { (void)f; (void)d; (void)l; return false; }
DPC_EXPORT int32_t iCloudForEachFile(void* h) { (void)h; return 0; }
DPC_EXPORT int32_t iCloudForEachChangedFile(void* h) { (void)h; return 0; }
DPC_EXPORT bool iCloudMarkCurrentVersionAsDownloaded(const char* f) { (void)f; return false; }
DPC_EXPORT bool iCloudReadFile(const char* f, void* d, int32_t* l) { (void)f; (void)d; if (l) *l = 0; return false; }
DPC_EXPORT bool iCloudDeleteFile(const char* f) { (void)f; return false; }

DPC_EXPORT bool GCStart(void* a, void* b, void* c) { (void)a; (void)b; (void)c; return false; }
DPC_EXPORT bool GCIsAuthenticated(void) { return false; }
DPC_EXPORT bool GCAreAchievementsReady(void) { return false; }
DPC_EXPORT bool GCSetAchievement(const char* id, bool show) { (void)id; (void)show; return false; }
DPC_EXPORT bool GCIsAchievementComplete(const char* id) { (void)id; return false; }
DPC_EXPORT bool GCSupportsRecurringLeaderboards(void) { return false; }
DPC_EXPORT bool GCSetLeaderboardScore(const char* id, int32_t s, int32_t c) { (void)id; (void)s; (void)c; return false; }
DPC_EXPORT bool GCRequestTopLeaderboardEntries(const char* id) { (void)id; return false; }
DPC_EXPORT bool GCRequestPlayerCenteredLeaderboardEntries(const char* id) { (void)id; return false; }
DPC_EXPORT bool GCRequestLocalLeaderboardEntry(const char* id) { (void)id; return false; }
DPC_EXPORT bool GCRequestFriendLeaderboardEntries(const char* id) { (void)id; return false; }
DPC_EXPORT bool GCIsLeaderboardRequestFinished(void) { return true; }
DPC_EXPORT int32_t GCGetDownloadedLeaderboardEntryCount(void) { return 0; }
DPC_EXPORT int64_t GCGetTotalLeaderboardEntryCount(void) { return 0; }
DPC_EXPORT bool GCGetRetrievedLeaderboardEntry(int32_t idx, void** id, void** name, int32_t* s, int64_t* r, int32_t* c, bool* l, bool* f) {
    (void)idx; (void)id; (void)name; (void)s; (void)r; (void)c; (void)l; (void)f;
    return false;
}
DPC_EXPORT void GCResetAchievements(void) {}
DPC_EXPORT bool GCIsAccessPointAvailable(void) { return false; }
DPC_EXPORT void GCShowAccessPoint(void) {}
DPC_EXPORT void GCHideAccessPoint(void) {}
DPC_EXPORT void GCSelectAccessPoint(void) {}
DPC_EXPORT float GCGetAccessPointOriginX(void) { return 0.0f; }
DPC_EXPORT float GCGetAccessPointOriginY(void) { return 0.0f; }
DPC_EXPORT float GCGetAccessPointSizeWidth(void) { return 0.0f; }
DPC_EXPORT float GCGetAccessPointSizeHeight(void) { return 0.0f; }
DPC_EXPORT bool GCOpenLeaderboardView(const char* id) { (void)id; return false; }
DPC_EXPORT bool GCIsUserUnderage(void) { return false; }
