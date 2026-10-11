"""Database benchmark for CourseCompass. Prints markdown tables you can paste into the QA report.

    python backend/tests/db/benchmark_db.py

READ-ONLY on your real tables. The index and vector experiments use TEMP tables
inside a transaction that is rolled back, so nothing is saved.

Two kinds of time are reported for each query:
  * client  = what your laptop sees (includes network round trip to Cloud SQL)
  * server  = the database's own execution time (EXPLAIN ANALYZE), no network
The gap between them is mostly network latency, not database work.
"""

import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

import psycopg
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())
DATABASE_URL = os.environ["DATABASE_URL"]

EMAIL = "nearly.done@example.edu"
COURSE = "MSSE 692"
TERM = "2027 SPR 8W1"
RUNS = 30
WARMUP = 3
SYNTHETIC_TX_ROWS = 100_000
SYNTHETIC_VECTORS = 2_000
LOAD_LEVELS = [1, 5, 10, 20]
LOAD_QUERIES_PER_WORKER = 25

QUERIES = {
    "course lookup by code": ("SELECT * FROM courses WHERE code = %s", (COURSE,)),
    "credits completed for a student": (
        (
            "SELECT COALESCE(SUM(c.credits), 0) FROM transcript_entries t "
            "JOIN courses c ON c.course_id = t.course_id JOIN students s ON s.student_id = t.student_id "
            "WHERE s.email = %s AND t.status = 'completed'"
        ),
        (EMAIL,)),
    "remaining required courses (audit)": (
        (
            "SELECT c.code FROM requirements r JOIN courses c ON c.course_id = r.course_id "
            "JOIN students s ON s.program_id = r.program_id WHERE s.email = %s AND NOT EXISTS ("
            "SELECT 1 FROM transcript_entries t WHERE t.student_id = s.student_id "
            "AND t.course_id = r.course_id AND t.status = 'completed')"
        ),
        (EMAIL,)),
    "prerequisites of a course": (
        (
            "SELECT pc.code FROM prerequisites p JOIN courses c ON c.course_id = p.course_id "
            "JOIN courses pc ON pc.course_id = p.prerequisite_course_id WHERE c.code = %s"
        ),
        (COURSE,)),
    "missing prerequisites for a student": (
        (
            "SELECT pc.code FROM prerequisites p JOIN courses c ON c.course_id = p.course_id "
            "JOIN courses pc ON pc.course_id = p.prerequisite_course_id WHERE c.code = %s AND NOT EXISTS ("
            "SELECT 1 FROM transcript_entries t JOIN students s ON s.student_id = t.student_id "
            "WHERE s.email = %s AND t.course_id = p.prerequisite_course_id AND t.status = 'completed')"
        ),
        (COURSE, EMAIL)),
    "courses offered in a term": (
        (
            "SELECT c.code, c.title FROM course_offerings o JOIN courses c ON c.course_id = o.course_id "
            "JOIN terms t ON t.term_id = o.term_id WHERE t.term_name = %s"
        ),
        (TERM,)),
    "syllabus chunks for a course": (
        (
            "SELECT chunk_index, chunk_text FROM syllabus_chunks s JOIN courses c ON c.course_id = s.course_id "
            "WHERE c.code = %s ORDER BY chunk_index"
        ),
        (COURSE,)),
}


def pct(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, round(p / 100 * (len(values) - 1)))]


def client_times(conn, sql, params, runs=RUNS):
    for _ in range(WARMUP):
        conn.execute(sql, params).fetchall()
    out = []
    for _ in range(runs):
        t0 = time.perf_counter()
        conn.execute(sql, params).fetchall()
        out.append((time.perf_counter() - t0) * 1000)
    return out


def explain(conn, sql, params):
    """Returns (server execution ms, top plan node type). ClientCursor allows parameters in EXPLAIN."""
    cur = psycopg.ClientCursor(conn)
    cur.execute("EXPLAIN (ANALYZE, FORMAT JSON) " + sql, params)
    plan = cur.fetchone()[0][0]
    return plan["Execution Time"], scan_node(plan["Plan"])


def scan_node(node):
    """First node that reads a table or index, e.g. 'Seq Scan' or 'Index Scan'."""
    if "Relation Name" in node:
        return node["Node Type"]
    for child in node.get("Plans", []):
        found = scan_node(child)
        if found:
            return found
    return node["Node Type"]


def table(headers, rows):
    print("| " + " | ".join(headers) + " |")
    print("|" + "|".join("---" for _ in headers) + "|")
    for r in rows:
        print("| " + " | ".join(str(x) for x in r) + " |")
    print()


def section_environment(conn):
    print("## Environment\n")
    version = conn.execute("SELECT version()").fetchone()[0].split(",")[0]
    maxc = int(conn.execute("SHOW max_connections").fetchone()[0])
    sb = conn.execute("SHOW shared_buffers").fetchone()[0]
    counts = {t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
              for t in ("courses", "prerequisites", "transcript_entries", "syllabus_chunks")}
    table(["Item", "Value"], [["Server", version], ["max_connections", maxc], ["shared_buffers", sb],
                              ["Rows", ", ".join(f"{k}={v}" for k, v in counts.items())],
                              ["Runs per query", f"{RUNS} (after {WARMUP} warm-ups)"]])
    return maxc


def section_query_timings(conn):
    print("## A. Query execution times (real tables)\n")
    rows = []
    for name, (sql, params) in QUERIES.items():
        times = client_times(conn, sql, params)
        server = [explain(conn, sql, params)[0] for _ in range(5)]
        node = explain(conn, sql, params)[1]
        rows.append([name, f"{statistics.median(times):.1f}", f"{pct(times, 95):.1f}",
                     f"{statistics.median(server):.3f}", node])
    table(["Query", "Client median (ms)", "Client p95 (ms)", "Server median (ms)", "Scan type"], rows)
    print("_Client time includes the network round trip; server time is the database's own work._\n")


def section_index_impact(conn):
    print(f"## B. Index impact (synthetic table, {SYNTHETIC_TX_ROWS:,} rows, same shape as transcript_entries)\n")
    conn.execute("CREATE TEMP TABLE bench_ids AS SELECT gen_random_uuid() AS sid FROM generate_series(1, %s)", (SYNTHETIC_TX_ROWS // 20,))
    conn.execute("CREATE TEMP TABLE bench_tx AS SELECT gen_random_uuid() AS entry_id, sid AS student_id, "
                 "gen_random_uuid() AS course_id, 'Fall 2026'::varchar AS term, 'completed'::varchar AS status "
                 "FROM bench_ids, generate_series(1, 20)")
    conn.execute("ANALYZE bench_tx")
    sid = conn.execute("SELECT sid FROM bench_ids LIMIT 1").fetchone()[0]
    sql, params = "SELECT count(*) FROM bench_tx WHERE student_id = %s", (sid,)

    before = [explain(conn, sql, params) for _ in range(10)]
    conn.execute("CREATE INDEX bench_tx_student_idx ON bench_tx (student_id)")
    conn.execute("ANALYZE bench_tx")
    after = [explain(conn, sql, params) for _ in range(10)]
    b, a = statistics.median(x[0] for x in before), statistics.median(x[0] for x in after)
    table(["Lookup by student_id", "Server median (ms)", "Plan"],
          [["Without index", f"{b:.3f}", before[-1][1]], ["With index", f"{a:.3f}", after[-1][1]],
           ["Speed-up", f"{b / a:.0f}x" if a else "n/a", ""]])
    print("_Our real tables are tiny (a dozen rows each), so queries finish in well under a millisecond with or without "
          "an index. This synthetic test shows how much the indexes matter once tables grow._\n")
    conn.rollback()


def section_vector_search(conn):
    print(f"## C. pgvector search ({SYNTHETIC_VECTORS:,} synthetic 768-dim vectors)\n")
    nulls = conn.execute("SELECT count(*) FILTER (WHERE embedding IS NOT NULL), count(*) FROM syllabus_chunks").fetchone()
    print(f"_Real syllabus_chunks rows with embeddings: {nulls[0]} of {nulls[1]}. The test below uses synthetic vectors "
          f"because real embeddings may not exist yet._\n")
    conn.execute("CREATE TEMP TABLE bench_vec (id serial PRIMARY KEY, embedding vector(768))")
    conn.execute("INSERT INTO bench_vec (embedding) SELECT (SELECT array_agg(random()::real + (g.g * 0)::real + (i * 0)::real) "
                 "FROM generate_series(1, 768) AS i)::vector(768) FROM generate_series(1, %s) AS g(g)", (SYNTHETIC_VECTORS,))
    conn.execute("ANALYZE bench_vec")
    q = "SELECT id FROM bench_vec ORDER BY embedding <=> (SELECT embedding FROM bench_vec WHERE id = %s) LIMIT 5"
    probes = list(range(1, 11))

    exact_ms, exact_sets = [], {}
    for p in probes:
        exact_ms.append(explain(conn, q, (p,))[0])
        exact_sets[p] = {r[0] for r in conn.execute(q, (p,)).fetchall()}

    conn.execute("CREATE INDEX ON bench_vec USING ivfflat (embedding vector_cosine_ops) WITH (lists = 20)")
    conn.execute("SET LOCAL ivfflat.probes = 5")
    conn.execute("ANALYZE bench_vec")
    idx_ms, recall = [], []
    for p in probes:
        ms, _scan = explain(conn, q, (p,))
        idx_ms.append(ms)
        got = {r[0] for r in conn.execute(q, (p,)).fetchall()}
        recall.append(len(got & exact_sets[p]) / 5)
    table(["Search type", "Server median (ms)", "Recall@5"],
          [["Exact scan (no index)", f"{statistics.median(exact_ms):.2f}", "100%"],
           ["ivfflat index (lists=20, probes=5)", f"{statistics.median(idx_ms):.2f}", f"{statistics.mean(recall) * 100:.0f}%"]])
    conn.rollback()


def load_worker(n_queries, sql, params):
    latencies = []
    with psycopg.connect(DATABASE_URL) as c:
        for _ in range(n_queries):
            t0 = time.perf_counter()
            c.execute(sql, params).fetchall()
            latencies.append((time.perf_counter() - t0) * 1000)
    return latencies


def section_load(max_connections):
    print("## D. Concurrent load (each worker = its own connection)\n")
    sql, params = QUERIES["missing prerequisites for a student"]
    rows = []
    for workers in LOAD_LEVELS:
        if workers > max_connections - 10:
            rows.append([workers, "skipped", "", "", "", f"would exceed max_connections ({max_connections})"])
            continue
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(lambda _: load_worker(LOAD_QUERIES_PER_WORKER, sql, params), range(workers)))
        wall = time.perf_counter() - t0
        lat = [x for r in results for x in r]
        rows.append([workers, f"{len(lat) / wall:.0f}", f"{statistics.median(lat):.1f}", f"{pct(lat, 95):.1f}",
                     f"{max(lat):.1f}", "ok"])
    table(["Concurrent workers", "Queries/sec", "Median (ms)", "p95 (ms)", "Max (ms)", "Note"], rows)
    print("_Client-side timings from this machine. Opening each connection also costs time not shown here._\n")


def main():
    with psycopg.connect(DATABASE_URL) as conn:
        max_connections = section_environment(conn)
        section_query_timings(conn)
        section_index_impact(conn)
        section_vector_search(conn)
        conn.rollback()
    section_load(max_connections)


if __name__ == "__main__":
    main()
