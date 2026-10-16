"""Mesh hygiene counts are measurements on world snapshots, not QA verdicts."""
import unittest

from asset_pipeline.surface import topology

CUBE_VERTICES = [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]]
CUBE_FACES = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [2, 3, 7, 6], [0, 4, 7, 3], [1, 2, 6, 5]]


def counts(vertices=CUBE_VERTICES, faces=CUBE_FACES):
    return topology(dict(vertices=[list(v) for v in vertices], faces=[list(f) for f in faces]))


class MeshTopologyTest(unittest.TestCase):
    def test_closed_consistent_cube_is_clean(self):
        self.assertEqual(counts(), dict(triangles=12, boundary_edges=0, nonmanifold_edges=0,
                                        inconsistent_winding_edges=0, degenerate_faces=0,
                                        coincident_vertices=0))

    def test_each_defect_is_counted_separately(self):
        flipped = [CUBE_FACES[0][::-1]] + CUBE_FACES[1:]
        self.assertEqual(counts(faces=flipped)['inconsistent_winding_edges'], 4)
        self.assertEqual(counts(faces=CUBE_FACES[:1] + CUBE_FACES[2:])['boundary_edges'], 4)
        fin = counts(CUBE_VERTICES + [[0.5, -1, 0]], CUBE_FACES + [[0, 1, 8]])
        self.assertEqual((fin['nonmanifold_edges'], fin['boundary_edges']), (1, 2))
        sliver = counts(CUBE_VERTICES + [[2, 0, 0]], CUBE_FACES + [[0, 1, 8]])
        self.assertEqual(sliver['degenerate_faces'], 1)
        self.assertEqual(counts(CUBE_VERTICES + [[1, 1, 1]])['coincident_vertices'], 1)


if __name__ == "__main__":
    unittest.main()
