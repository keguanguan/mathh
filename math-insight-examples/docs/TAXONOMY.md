# Taxonomy of key ideas

The taxonomy lives in `data/taxonomy.yaml`; this page is a readable rendering of it
(regenerate with `python scripts/build_docs.py`). Every entry has exactly one main idea,
`key_idea.category`, which must be one of the ids below; additional ideas go in `tags`.
The `folder` column is where entries with that main idea are stored under `data/problems/`.

A problem is *not* filed under `invariant` just because an invariant appears somewhere in
the proof: the category names the observation that makes the problem collapse. When several
ideas cooperate (e.g. a parity invariant plus an induction), the category is the one a reader
would name first, and the others are tags.

| id | name | folder | entries |
|---|---|---|---:|
| `invariant` | Invariant | `invariants` | 6 |
| `parity_invariant` | &nbsp;&nbsp;&nbsp;&nbsp;Parity invariant | `parity` | 18 |
| `modular_invariant` | &nbsp;&nbsp;&nbsp;&nbsp;Modular invariant | `invariants` | 10 |
| `coloring_invariant` | &nbsp;&nbsp;&nbsp;&nbsp;Coloring invariant | `coloring` | 12 |
| `permutation_invariant` | &nbsp;&nbsp;&nbsp;&nbsp;Permutation invariant | `invariants` | 1 |
| `algebraic_invariant` | &nbsp;&nbsp;&nbsp;&nbsp;Algebraic invariant | `invariants` | 5 |
| `group_invariant` | &nbsp;&nbsp;&nbsp;&nbsp;Group invariant | `invariants` | 2 |
| `geometric_invariant` | &nbsp;&nbsp;&nbsp;&nbsp;Geometric invariant | `invariants` | 4 |
| `conservation_law` | &nbsp;&nbsp;&nbsp;&nbsp;Conservation law | `invariants` | 4 |
| `monovariant` | Monovariant / potential function | `monovariants` | 8 |
| `potential_function` | &nbsp;&nbsp;&nbsp;&nbsp;Potential function | `monovariants` | 2 |
| `smoothing` | &nbsp;&nbsp;&nbsp;&nbsp;Smoothing / local improvement | `monovariants` | 8 |
| `symmetry` | Symmetry | `symmetry` | 14 |
| `pairing_strategy` | &nbsp;&nbsp;&nbsp;&nbsp;Pairing / mirror strategy | `symmetry` | 9 |
| `involution_parity` | &nbsp;&nbsp;&nbsp;&nbsp;Involution / pairing-off argument | `symmetry` | 6 |
| `extremal_principle` | Extremal principle | `extremal` | 27 |
| `infinite_descent` | &nbsp;&nbsp;&nbsp;&nbsp;Infinite descent / minimal counterexample | `extremal` | 8 |
| `pigeonhole` | Pigeonhole principle | `combinatorial` | 28 |
| `representation_change` | Representation change | `representation_change` | 11 |
| `geometric_reinterpretation` | &nbsp;&nbsp;&nbsp;&nbsp;Geometric reinterpretation | `representation_change` | 8 |
| `graph_reinterpretation` | &nbsp;&nbsp;&nbsp;&nbsp;Graph reinterpretation | `representation_change` | 9 |
| `algebraic_encoding` | &nbsp;&nbsp;&nbsp;&nbsp;Algebraic encoding | `representation_change` | 25 |
| `coordinate_transformation` | &nbsp;&nbsp;&nbsp;&nbsp;Coordinate transformation | `representation_change` | 7 |
| `isomorphism_to_another_problem` | &nbsp;&nbsp;&nbsp;&nbsp;Isomorphism to another problem | `representation_change` | 7 |
| `combinatorial_interpretation` | &nbsp;&nbsp;&nbsp;&nbsp;Combinatorial interpretation | `representation_change` | 4 |
| `generating_function` | &nbsp;&nbsp;&nbsp;&nbsp;Generating function | `representation_change` | 2 |
| `complex_or_vector_coordinates` | &nbsp;&nbsp;&nbsp;&nbsp;Complex numbers / vectors | `representation_change` | 8 |
| `decomposition` | Decomposition | `geometric` | 20 |
| `recursive_structure` | Recursive structure | `other` | 12 |
| `induction` | Induction | `other` | 15 |
| `structural_obstruction` | Contradiction via structural obstruction | `other` | 14 |
| `strategy_stealing` | &nbsp;&nbsp;&nbsp;&nbsp;Strategy stealing | `other` | 2 |
| `diagonalization` | &nbsp;&nbsp;&nbsp;&nbsp;Diagonalization / self-reference | `other` | 2 |
| `information_counting_bound` | &nbsp;&nbsp;&nbsp;&nbsp;Information / counting bound | `other` | 5 |
| `bijection` | Bijection | `combinatorial` | 24 |
| `double_counting` | Double counting | `combinatorial` | 28 |
| `inclusion_exclusion` | &nbsp;&nbsp;&nbsp;&nbsp;Inclusion-exclusion | `combinatorial` | 4 |
| `probabilistic_argument` | Probabilistic argument | `combinatorial` | 11 |
| `linearity_of_expectation` | &nbsp;&nbsp;&nbsp;&nbsp;Linearity of expectation | `combinatorial` | 7 |
| `geometric_transformation` | Geometric transformation | `geometric` | 0 |
| `reflection` | &nbsp;&nbsp;&nbsp;&nbsp;Reflection | `geometric` | 6 |
| `rotation` | &nbsp;&nbsp;&nbsp;&nbsp;Rotation | `geometric` | 2 |
| `homothety_or_inversion` | &nbsp;&nbsp;&nbsp;&nbsp;Homothety / inversion / projective map | `geometric` | 5 |
| `unfolding` | &nbsp;&nbsp;&nbsp;&nbsp;Unfolding | `geometric` | 2 |
| `continuous_deformation` | &nbsp;&nbsp;&nbsp;&nbsp;Continuous deformation / degenerate case | `geometric` | 3 |
| `number_theoretic_structure` | Number-theoretic structure | `number_theoretic` | 6 |
| `gcd_structure` | &nbsp;&nbsp;&nbsp;&nbsp;gcd structure | `number_theoretic` | 6 |
| `dynamical_systems` | Dynamical systems viewpoint | `dynamical` | 0 |
| `circle_rotation` | &nbsp;&nbsp;&nbsp;&nbsp;Rotation of the circle / linear flow on a torus | `dynamical` | 4 |
| `finite_state_periodicity` | &nbsp;&nbsp;&nbsp;&nbsp;Finite state space forces periodicity | `dynamical` | 7 |
| `attracting_structure` | &nbsp;&nbsp;&nbsp;&nbsp;Attracting structure / collapse of orbits | `dynamical` | 5 |
| `auxiliary_object` | Auxiliary object | `other` | 29 |
| `algebraic_identity` | Algebraic identity | `algebraic` | 8 |
| `telescoping` | &nbsp;&nbsp;&nbsp;&nbsp;Telescoping | `algebraic` | 10 |
| `grouping_terms` | &nbsp;&nbsp;&nbsp;&nbsp;Grouping / comparison of terms | `algebraic` | 5 |
| `factorisation` | &nbsp;&nbsp;&nbsp;&nbsp;Factorisation | `algebraic` | 11 |
| `other` | Other | `other` | 0 |

## Descriptions and examples

### `invariant` — Invariant

A quantity that no allowed move can change. If the target state has a different value of the quantity than the start, the target is unreachable; if the quantity determines the final state, the outcome is forced.

Entries: `am_hm_iteration_geometric_mean`, `binary_search_loop_invariant`, `breaking_chocolate`, `brussels_sprouts_fixed_length`, `reservoir_sampling_invariant`, `stones_split_piles_invariant`

#### `parity_invariant` — Parity invariant

A count whose parity (odd/even) is preserved by every move.

Entries: `bipartite_iff_no_odd_cycle`, `changing_colors_rows_columns`, `chocolate_breaking_game_parity`, `eight_rooks_black_squares_even`, `erase_two_write_difference`, `fixed_length_games_parity`, `flipping_n_minus_one_of_n_triangles`, `frog_jumps_increasing_lengths_return`, `jordan_curve_polygon_ray_parity`, `moving_chips_in_pairs`, `parity_bit_single_error_detection`, `plus_or_minus`, `rows_columns_products_sum_nonzero`, `seven_cups_flip_four`, `solitaire_on_a_circle`, `squares_and_circles`, `squares_circles_triangles`, `white_and_black_balls_urn`

#### `modular_invariant` — Modular invariant

A quantity preserved modulo m for some m > 2.

Entries: `chameleons`, `check_digit_modular_invariant`, `digit_reversal_divisible_by_nine`, `digit_sum_iteration_imo1975`, `divisibility_by_eleven_alternating_sum`, `dragon_heads_mod_three`, `pythagorean_triple_divisibility_3_4_5`, `squares_mod_four_obstruction`, `sum_of_three_cubes_mod_nine`, `sum_of_two_odd_squares_not_square`

#### `coloring_invariant` — Coloring invariant

Color the cells/points so that every allowed piece or move interacts with the colors in a fixed way; then compare color counts.

Entries: `bicubal_domino_centre_removed`, `cube_vertex_walk_parity`, `grasshoppers_triangular_board`, `knight_returns_even_moves`, `knights_5x5_simultaneous_move`, `knights_tour_4xn_closed`, `mutilated_checkerboard`, `rectangle_integer_side_tiling`, `straight_tetromino_10x10`, `straight_tromino_deficient_board`, `t_tetromino_10x10`, `vertical_horizontal_dominoes_even`

#### `permutation_invariant` — Permutation invariant

The sign (parity) of a permutation, or a similar group-theoretic label, is preserved by every move.

Entries: `fifteen_puzzle`

#### `algebraic_invariant` — Algebraic invariant

An algebraic expression in the current numbers (a product, a sum of squares, a gcd, an XOR) is unchanged by every move.

Entries: `nim`, `rectangle_corner_product_invariant`, `rotation_transform_sum_of_squares`, `sums_and_products`, `two_by_two_block_flips_row_product`

#### `group_invariant` — Group invariant

Positions are labelled by elements of a finite group so that moves act trivially on the label.

Entries: `peg_solitaire`, `rubiks_cube_single_edge_flip`

#### `geometric_invariant` — Geometric invariant

An area, length, angle or ratio preserved by every move.

Entries: `exterior_angles_sum_360`, `log_area_scaling_invariance`, `pentagram_angle_sum_turning`, `three_pegs_area`

#### `conservation_law` — Conservation law

A global total (of weight, of threads, of energy) that is redistributed but never created or destroyed by moves.

Entries: `gamblers_ruin_fair_game`, `polya_urn_martingale`, `splitting_piles`, `wine_and_water_mixing`

### `monovariant` — Monovariant / potential function

A quantity that changes in only one direction with every move and is bounded, so the process must terminate or can never reach a state where the quantity would have to exceed its bound.

Entries: `candy_sharing_circle`, `egyptian_fraction_greedy_terminates`, `gale_shapley_stable_matching`, `inversions_adjacent_swaps`, `pentagon_sign_flipping_imo1986`, `sign_flipping_rows_columns`, `sprouts_game_bounded_length`, `two_rooms_half_friends`

#### `potential_function` — Potential function

A weighted sum over the configuration whose total is bounded above (or below) and compared against the target.

Entries: `conway_soldiers`, `escape_of_the_clones`

#### `smoothing` — Smoothing / local improvement

Moving two variables closer together (or swapping a pair) improves the objective, so the optimum is attained at an equal or sorted configuration.

Entries: `chebyshev_sum_inequality_rearrangement`, `cut_property_minimum_spanning_tree`, `fixed_sum_maximise_product_smoothing`, `imo1978_rearrangement_sum`, `interval_scheduling_earliest_finish`, `largest_inscribed_triangle_equilateral`, `rearrangement_inequality_swapping`, `turan_theorem_zykov_symmetrisation`

### `symmetry` — Symmetry

Exploit a symmetry of the problem: pair objects with their mirror images, reverse a sum, or copy the opponent's move.

Entries: `expected_maximum_uniforms_spacings`, `first_ace_expected_position_symmetry`, `gauss_pairing_sum`, `i_cut_you_choose_fair_division`, `integral_symmetry_sin_over_sin_plus_cos`, `isosceles_base_angles_pappus_reflection`, `knights_and_knaves_double_question`, `penney_game_prefix_strategy`, `point_reflections_return_after_six`, `random_walk_cycle_last_vertex_uniform`, `reflection_across_two_parallel_lines_translation`, `regular_polygon_vectors_sum_zero`, `three_random_points_semicircle`, `von_neumann_fair_coin_from_biased`

#### `pairing_strategy` — Pairing / mirror strategy

A game strategy that answers each move with its symmetric partner.

Entries: `coins_in_a_row_parity_strategy`, `coins_on_round_table`, `divisor_naming_game_pairing`, `domino_placing_game_mirror`, `kayles_mirror_strategy`, `one_pile_take_at_most_k_or_double_scoring`, `proizvolov_identity`, `subtraction_game_complement`, `thirty_two_knights_maximum`

#### `involution_parity` — Involution / pairing-off argument

Pair the elements of a finite set by an involution; the unpaired elements (fixed points) have the same parity as the whole set, so a statement about the set reduces to a statement about the fixed points.

Entries: `divisor_means_product_identity`, `divisors_odd_iff_square`, `hundred_lockers_puzzle`, `number_of_divisors_at_most_2_sqrt_n`, `wilson_theorem_pairing`, `zagier_two_squares_involution`

### `extremal_principle` — Extremal principle

Look at the largest, smallest, closest or first object. Its extremality forces a property that no other object need have.

Entries: `cauchy_bound_on_roots`, `convex_polygon_in_rectangle_area_two`, `dirac_hamiltonian_min_degree`, `eulerian_circuit_longest_trail`, `gas_stations_circular_track`, `handshake_puzzle_hosts_spouse`, `happy_ending_five_points_convex_quadrilateral`, `harmonic_sum_not_integer`, `helly_one_dimensional_intervals`, `infinite_monotone_subsequence`, `lame_theorem_euclid_steps`, `longest_path_min_degree_cycle`, `max_distance_pairs_at_most_n`, `n_does_not_divide_2n_minus_1`, `nearest_neighbour_graph_no_cycle`, `no_finite_set_all_midpoints`, `non_crossing_red_blue_matching`, `odd_number_of_shooters`, `points_in_triangle_of_area_four`, `rolle_theorem_via_extremum`, `sharygin_criminal_ministers`, `sylvester_gallai`, `tangent_perpendicular_to_radius`, `ten_coins_triangle_invert_three_moves`, `tournament_hamiltonian_path`, `tournament_king`, `triangle_inequality_from_shortest_path`

#### `infinite_descent` — Infinite descent / minimal counterexample

Assume a smallest counterexample and construct a smaller one.

Entries: `four_pegs_square_reversibility`, `fundamental_theorem_arithmetic_uniqueness`, `golden_ratio_irrational_rectangle_descent`, `no_solutions_x2_y2_3z2`, `regular_pentagon_lattice_descent`, `sqrt2_irrational_descent`, `vieta_jumping_imo1988`, `x2_y2_z2_2xyz_descent`

### `pigeonhole` — Pigeonhole principle

Partition into fewer boxes than objects; two objects share a box. The art is choosing the boxes.

Entries: `art_gallery_fisk`, `circle_ten_numbers_three_consecutive`, `dirichlet_approximation`, `erdos_szekeres_monotone_subsequence`, `expected_value_argument_someone_above_average`, `fifty_five_numbers_differ_by_ten`, `fifty_two_integers_sum_or_difference`, `five_lattice_points_midpoint`, `five_points_sphere_hemisphere`, `five_points_unit_square`, `fourteen_bishops_maximum`, `kissing_number_plane_six`, `lossless_compression_pigeonhole`, `misplaced_name_cards_rotation`, `multiple_with_only_ones_and_zeros`, `n_plus_one_from_2n_coprime`, `n_plus_one_from_2n_divisibility`, `party_of_six_ramsey`, `polyhedron_two_faces_same_edge_count`, `same_number_of_acquaintances`, `seven_reals_arctan_pigeonhole`, `seventeen_points_three_colours`, `sixteen_kings_maximum`, `subset_sum_divisible_by_n`, `ten_two_digit_numbers_equal_sums`, `three_by_seven_monochromatic_rectangle`, `triangle_ten_points_side_one`, `two_colour_plane_unit_distance`

### `representation_change` — Representation change

Re-encode the problem so that the awkward rule becomes a familiar one.

Entries: `base_rate_natural_frequencies`, `bertrand_paradox_random_chord`, `boy_or_girl_sample_space`, `burning_ropes_forty_five_minutes`, `efron_nontransitive_dice`, `hourglasses_four_and_seven_measure_nine`, `hundred_prisoners_boxes_cycles`, `inspection_paradox_bus_waiting`, `simpson_paradox_weighted_averages`, `two_envelopes_paradox`, `two_trains_and_a_fly`

#### `geometric_reinterpretation` — Geometric reinterpretation

Turn a non-geometric statement into a picture.

Entries: `broken_stick_triangle_probability`, `circumcentre_perpendicular_bisectors`, `ford_circles`, `ladder_midpoint_traces_circle`, `lozenge_tiling_hexagon_three_orientations`, `monge_theorem_three_dimensions`, `pythagorean_triples_rational_points`, `two_monks_mountain`

#### `graph_reinterpretation` — Graph reinterpretation

Model the objects as vertices and the relations as edges.

Entries: `bridges_of_konigsberg`, `de_bruijn_sequence_eulerian`, `guarini_four_knights`, `instant_insanity_graph`, `looping_chips_unfolding`, `petersen_word_puzzle_hamiltonian`, `schur_theorem_via_ramsey`, `seven_coins_star_polygon`, `wolf_goat_cabbage_state_graph`

#### `algebraic_encoding` — Algebraic encoding

Encode configurations as numbers, polynomials, binary strings or coordinates so that moves become arithmetic.

Entries: `apollonius_circle_ratio_locus`, `bachet_weights_balanced_ternary`, `bags_of_coins_one_weighing`, `calendar_magic`, `cassini_identity_matrix_determinant`, `chaos_game_sierpinski_addresses`, `doubling_map_binary_expansion`, `fibonacci_nim_zeckendorf`, `gcd_times_lcm_exponents`, `grundy_game_sprague_grundy_values`, `hamming_three_hats_strategy`, `imo1962_moving_last_digit_to_front`, `josephus_binary`, `lamps_in_a_row_chasing`, `lights_out_linear_algebra`, `lucas_theorem_binomial_parity`, `oddtown_clubs`, `pell_equation_infinitely_many_solutions`, `poisoned_wine_binary_testing`, `prisoners_hats_parity`, `radical_axis_subtract_equations`, `radical_centre_common_chords_concurrent`, `reverse_and_add_1089_trick`, `sock_drawer_probability_mosteller`, `wythoff_nim_beatty`

#### `coordinate_transformation` — Coordinate transformation

Choose coordinates in which the problem becomes trivial.

Entries: `ant_on_a_rubber_rope`, `clock_hands_overlap_eleven`, `coin_rotation_paradox`, `depressed_cubic_substitution`, `four_bugs_pursuit`, `gaussian_integral_squared_polar`, `shape_of_area_less_than_one_avoids_lattice`

#### `isomorphism_to_another_problem` — Isomorphism to another problem

Recognise the problem as a known problem in disguise.

Entries: `ants_on_a_stick`, `fif`, `misere_nim_bouton_rule`, `nimble_is_nim`, `northcotts_game_nim`, `silver_dollar_game_gaps`, `turning_turtles`

#### `combinatorial_interpretation` — Combinatorial interpretation

Read an algebraic or arithmetic quantity as the size of a set, so that its properties (integrality, an identity) become obvious.

Entries: `binomial_theorem_choosing_factors`, `consecutive_product_divisible_by_factorial`, `fermat_little_theorem_necklaces`, `fibonacci_tilings_identity`

#### `generating_function` — Generating function

Encode a sequence as the coefficients of a power series so that a combinatorial statement becomes an identity of functions.

Entries: `even_number_of_heads_biased_coin`, `partitions_odd_parts_equal_distinct_parts`

#### `complex_or_vector_coordinates` — Complex numbers / vectors

Represent points as complex numbers or vectors so that rotations, centroids and similarity become one-line algebra.

Entries: `brahmagupta_fibonacci_identity`, `centroid_minimises_sum_of_squared_distances`, `medians_concur_centroid_vectors`, `medians_form_a_triangle_vectors`, `napoleon_theorem_complex`, `parallelogram_law_vectors`, `three_squares_arctan_complex`, `varignon_parallelogram`

### `decomposition` — Decomposition

Cut the object into pieces whose contributions are individually obvious.

Entries: `angle_bisector_theorem_by_areas`, `ceva_theorem_by_areas`, `circle_area_unrolling_triangle`, `cyclic_quadrilateral_opposite_angles`, `geometric_series_half_square_picture`, `harmonic_numbers_versus_log_integral`, `inradius_area_semiperimeter`, `inscribed_angle_theorem_central_angle`, `meno_doubling_the_square`, `pyramid_volume_one_third_prism`, `pythagoras_by_scaling`, `rhombus_inscribed_circle_tangent_lengths`, `sphere_volume_cavalieri_hatbox`, `sum_of_angles_of_polygon_triangulation`, `sum_of_first_n_odd_numbers`, `tetrahedron_in_cube_volume`, `thales_angle_in_semicircle`, `two_triangular_numbers_make_square`, `viviani_theorem`, `young_inequality_areas`

### `recursive_structure` — Recursive structure

The problem contains a smaller copy of itself; solve by reducing to it.

Entries: `binary_strings_no_consecutive_ones`, `bolzano_weierstrass_bisection`, `derangement_recursion_hat_of_first_person`, `domino_tilings_2xn_fibonacci`, `geometric_waiting_time_conditioning`, `gray_code_hypercube_hamiltonian`, `hh_versus_ht_waiting_times`, `infinite_power_tower_equals_two`, `n_heads_in_a_row_expected_tosses`, `noncrossing_handshakes_catalan_recursion`, `tower_of_hanoi`, `tower_of_hanoi_adjacent_moves`

### `induction` — Induction

Choose the right induction variable and the right way to grow the object.

Entries: `am_gm_cauchy_forward_backward_induction`, `bernoulli_inequality_induction`, `blue_eyed_islanders_induction`, `cauchy_functional_equation_rationals`, `euler_formula_planar`, `induction_strengthening_basel_bound`, `l_tromino_deficient_board`, `lines_in_general_position_regions`, `pick_theorem_additivity`, `pirate_game_backward_induction`, `planar_graph_six_colourable`, `ramsey_two_colour_upper_bound_recursion`, `tree_has_n_minus_one_edges`, `two_colouring_line_arrangement`, `zeckendorf_greedy`

### `structural_obstruction` — Contradiction via structural obstruction

Suppose the object exists and derive a contradiction from a structural feature (a forced overlap, a forced count, a forced strategy).

Entries: `average_speed_uphill_downhill`, `bridge_and_torch`, `champernowne_irrational`, `cube_cuts_twenty_seven`, `curry_paradox_missing_square`, `egg_drop_two_eggs`, `equilateral_triangle_lattice_impossible`, `fault_free_6x6_domino_tiling`, `hex_no_draw`, `log2_of_3_irrational`, `look_and_say_no_digit_four`, `n_edges_n_vertices_cycle`, `odd_degree_polynomial_real_root`, `sim_game_no_draw_ramsey`

#### `strategy_stealing` — Strategy stealing

If the second player had a winning strategy the first player could steal it, so the first player wins (non-constructively).

Entries: `chomp_strategy_stealing`, `tic_tac_toe_first_player_cannot_lose`

#### `diagonalization` — Diagonalization / self-reference

Build an object that differs from the k-th listed object in the k-th place, so no list can be complete.

Entries: `cantor_diagonal_uncountable`, `halting_problem_diagonal`

#### `information_counting_bound` — Information / counting bound

A procedure with k steps of b outcomes each can distinguish at most b^k cases; compare with the number of cases to be distinguished.

Entries: `census_taker_ages_product_36`, `mislabeled_boxes_one_draw`, `nine_coins_two_weighings_ternary`, `twelve_coins_information_bound`, `twenty_questions_information_bound`

### `bijection` — Bijection

Count something else that is in one-to-one correspondence with the objects of interest.

Entries: `ballot_theorem_reflection`, `cantor_schroder_bernstein_chains`, `catalan_dyck_paths_reflection`, `cayley_formula_prufer`, `chinese_remainder_bijection`, `countable_union_of_countable_sets`, `diagonal_intersections_convex_polygon`, `divisor_functions_multiplicative_bijection`, `euclid_even_perfect_numbers`, `even_and_odd_subsets`, `fermat_little_theorem_multiply_residues`, `fisher_yates_shuffle_uniform`, `hilbert_hotel_infinite_guests`, `lattice_paths_binomial`, `mosers_circle_regions`, `pascal_rule_contains_element_or_not`, `rationals_countable_zigzag`, `rectangles_on_chessboard_choose_lines`, `squares_on_a_chessboard_204`, `stars_and_bars`, `subsets_binary_strings`, `tennis_tournament_matches`, `tic_tac_toe_3d_winning_lines`, `totient_sum_over_divisors`

### `double_counting` — Double counting

Count the same set in two ways and equate the results.

Entries: `burnside_necklaces_prime_beads`, `committee_with_chair`, `counting_diagonals_convex_polygon`, `diagonals_of_polygon_count`, `erdos_ko_rado_katona_circle`, `five_platonic_solids`, `friendship_paradox_cauchy_schwarz`, `hall_marriage_regular_bipartite_matching`, `handshake_lemma`, `hockey_stick_largest_element`, `imo1987_permutations_fixed_points_sum`, `magic_square_centre_five`, `mantel_triangle_free`, `nicomachus_sum_of_cubes`, `no_four_cycle_edge_bound_cherries`, `pins_chain_head_head_equals_tail_tail`, `planar_graph_edge_bound`, `planar_graph_vertex_degree_five`, `regular_bipartite_equal_sides`, `regular_polygon_tilings_of_plane`, `sperner_antichain_lym`, `sperner_lemma_doors`, `sum_of_binomial_squares_central`, `sum_of_prime_reciprocals_diverges_erdos`, `three_utilities_problem_nonplanar`, `toads_and_frogs_move_count`, `trailing_zeros_factorial`, `vandermonde_committees`

#### `inclusion_exclusion` — Inclusion-exclusion

Count a union by adding and subtracting intersections; the sign pattern makes an unwieldy count mechanical.

Entries: `derangements_inclusion_exclusion`, `euler_phi_inclusion_exclusion`, `spherical_triangle_area_lunes`, `surjections_inclusion_exclusion`

### `probabilistic_argument` — Probabilistic argument

Show an object exists by showing a random object has the property with positive probability, or by comparing an expectation with a bound.

Entries: `bertrand_box_paradox`, `bipartite_subgraph_half_edges`, `birthday_paradox_complement`, `buffon_needle_barbier`, `caro_wei_independent_set`, `hypergraph_two_colouring_random`, `monty_hall_switch`, `ramsey_lower_bound_random`, `secretary_problem_thirty_seven_percent`, `sum_free_subset_one_third`, `tournament_property_sk_random`

#### `linearity_of_expectation` — Linearity of expectation

Write the quantity as a sum of indicator variables; expectations add even when the indicators are dependent.

Entries: `coupon_collector_linearity`, `expected_cycles_random_permutation_harmonic`, `expected_number_of_runs_linearity`, `quicksort_expected_comparisons_indicators`, `random_permutation_fixed_points_expectation`, `random_walk_distance_sqrt_n`, `records_in_random_sequence_harmonic`

### `geometric_transformation` — Geometric transformation

Apply a reflection, rotation, translation, unfolding or dilation that straightens the problem out.

#### `reflection` — Reflection

Reflect a point or figure across a line to straighten a path.

Entries: `ellipse_reflection_property_heron`, `fagnano_orthic_triangle`, `herons_shortest_path`, `orthocentre_reflection_circumcircle`, `shortest_bisecting_arc_equilateral_triangle`, `shortest_fence_quarter_circle_reflection`

#### `rotation` — Rotation

Rotate part of the figure about a point so that separate segments line up into one path or one triangle.

Entries: `fermat_point_rotation`, `pompeiu_theorem_rotation`

#### `homothety_or_inversion` — Homothety / inversion / projective map

Apply a scaling, an inversion or a projective transformation that preserves the relevant structure but simplifies (or exposes) it.

Entries: `euler_line_homothety`, `inversion_circle_through_centre_to_line`, `nine_point_circle_homothety`, `ptolemy_theorem_equality_via_inversion`, `straightedge_alone_center_impossible`

#### `unfolding` — Unfolding

Flatten a surface so that a path on it becomes a straight line.

Entries: `spider_and_fly`, `string_around_cylinder_unfolding`

#### `continuous_deformation` — Continuous deformation / degenerate case

Sweep a parameter continuously; an intermediate-value or a degenerate configuration settles the question.

Entries: `napkin_ring`, `pancake_theorem_bisecting_line`, `wobbly_table_rotation_ivt`

### `number_theoretic_structure` — Number-theoretic structure

Divisibility, gcd, prime factorisation or residues carry the argument.

Entries: `doubling_the_cube_impossible`, `fermat_numbers_coprime_primes`, `frobenius_two_coins`, `infinitely_many_primes_euclid`, `primes_4k_plus_3_infinite`, `rational_root_theorem_divisibility`

#### `gcd_structure` — gcd structure

The set of reachable numbers is the set of multiples of a gcd.

Entries: `euclid_gcd_algorithm_invariant`, `euclids_game`, `fibonacci_gcd_identity`, `imo1959_fraction_irreducible`, `pairs_of_heaps_gcd_reachability`, `three_five_jug_water_pouring`

### `dynamical_systems` — Dynamical systems viewpoint

View a process as iterating a map, and ask about its orbits: where they go, whether they return, how they are distributed. The problem is solved by identifying the map with a well-understood one.

#### `circle_rotation` — Rotation of the circle / linear flow on a torus

After a change of variable (typically a logarithm or an unfolding) the process is x -> x + alpha on the circle, or a straight-line flow on a torus; irrational alpha gives dense, equidistributed orbits, rational alpha gives periodic ones.

Entries: `benford_leading_digits_powers_of_two`, `power_of_two_with_prescribed_leading_digits`, `sin_n_dense_in_interval`, `square_billiards_unfolding`

#### `finite_state_periodicity` — Finite state space forces periodicity

A deterministic map on a finite set must eventually repeat (pigeonhole in time); if the map is invertible the orbit is purely periodic, so it returns to its starting point.

Entries: `fibonacci_mod_m_periodic`, `floyd_cycle_detection_tortoise_hare`, `happy_numbers_eventually_periodic`, `imo1964_powers_of_two_mod_seven`, `last_digit_of_tower_of_sevens`, `perfect_shuffle_returns_eight`, `repeating_decimal_period_order`

#### `attracting_structure` — Attracting structure / collapse of orbits

Every orbit is forced onto a small invariant set (a fixed point, a cycle, or a lattice) by a monovariant or a modular argument.

Entries: `babylonian_square_root_monotone`, `cosine_iteration_contraction`, `ducci_four_number_game`, `kaprekar_6174_attractor`, `nested_radical_fixed_point`

### `auxiliary_object` — Auxiliary object

Introduce an extra object (a number, a tank of fuel, a second traveller) that is not in the problem but makes the argument visible.

Entries: `altitudes_concur_anticomplementary_triangle`, `antipodal_points_same_temperature`, `broken_line_in_triangle`, `cauchy_schwarz_discriminant`, `cos20_cos40_cos80_product`, `cube_face_diagonals_60_degrees`, `e_is_irrational_fourier`, `e_sequence_increasing_am_gm`, `equiangular_hexagon_side_differences`, `ferry_boats_meeting_distances`, `fixed_point_interval_ivt`, `gomory_opposite_colour_squares`, `hermite_identity_floor`, `intersecting_chords_similar_triangles`, `jensen_inequality_tangent_line`, `lagrange_interpolation_basis`, `law_of_sines_circumcircle`, `longest_segment_through_circle_intersection`, `markov_inequality_indicator_bound`, `n_consecutive_composites`, `negative_coconuts_monkey`, `nesbitt_inequality_am_hm`, `nth_root_of_n_tends_to_one`, `product_of_odd_over_even_bound`, `ptolemy_inequality_via_similar_triangles`, `sqrt2_plus_sqrt3_irrational`, `triangle_angle_sum_parallel_line`, `universal_chord_theorem`, `vandermonde_determinant_roots`

### `algebraic_identity` — Algebraic identity

Rewrite an expression in a form (telescoping sum, sum of squares, product) where the claim is visible.

Entries: `am_gm_two_variables_square`, `arbelos_area_equals_circle_on_altitude`, `isoperimetric_rectangle_am_gm`, `qm_am_inequality_sum_of_squares`, `rope_around_the_earth`, `sum_of_squares_inequality`, `titu_lemma_engel_form`, `triangle_fixed_perimeter_equilateral_heron`

#### `telescoping` — Telescoping

Write terms as differences so that a sum collapses.

Entries: `arctan_telescoping_sum`, `circle_arrangement_sum_of_differences_lower_bound`, `fibonacci_sum_telescoping`, `finite_differences_polynomial_degree`, `geometric_series_shift`, `sum_k_times_k_factorial`, `sum_n_over_2_to_n_shift`, `sum_of_squares_formula_telescoping_cubes`, `telescoping_product_one_minus_reciprocal_squares`, `telescoping_reciprocal_products`

#### `grouping_terms` — Grouping / comparison of terms

Group the terms of a sum into blocks that can each be bounded by the same simple quantity.

Entries: `four_consecutive_product_plus_one_square`, `harmonic_series_diverges_grouping`, `p_series_three_halves_telescoping_bound`, `st_petersburg_infinite_expectation`, `zeno_achilles_geometric_series`

#### `factorisation` — Factorisation

An algebraic factorisation exposes a divisor, so primality or divisibility questions become immediate.

Entries: `am_gm_three_variables_cubes`, `cubes_sum_factorisation_x_plus_y_plus_z`, `difference_of_two_squares_representable`, `mersenne_fermat_prime_shapes`, `odd_square_one_mod_eight`, `polynomial_difference_divisibility`, `prime_divides_binomial_coefficient`, `repunit_prime_digits_prime`, `six_divides_n_cubed_minus_n`, `sophie_germain_identity_composite`, `wilson_converse_composite_factorial`

### `other` — Other

Ideas that fit none of the categories above.

