export const examples = [{"name": "sample", "data": "{\n    // comments\n    mode: 48, // Sv3/9\n    // Sample JSON for running test cases\n    // memory_size: 0x8000000000,\n    test_cases: [\n        { repeats: 4 },\n        {\n            repeats: 4, // How many times to make the test case\n            // Probabilistic fields:\n            // same_va_pa: 0.05,\n            // // reuse_pte: 0.05,\n            // aliasing: 0.05,\n            // // VA and PA take the data\n            // va: 0x99301234,\n            // pa: 0x14231234,\n            ptes: [\n                {\n                    // PTE entry -- set the address + the PPNs\n                    address: 0x12399ff000,\n                    // ppns: [null, 0x119, null],\n                },\n                {},\n                {},\n                {\n                    attributes: {\n                        // Set the flags (RSW, DAGUXWRV) probabilistically on the PTE\n                        G: 0.5, // Float for probabilities\n                        U: 1, // 0 - 1 aren't probabilities\n                        X: 0.5, // Float for probabilities\n                        W: 0, // 0 - 1 aren't probabilities\n                        R: 1, // 0 - 1 aren't probabilities\n                    },\n                },\n            ],\n        },\n        {\n            same_va_pa: 1,\n        },\n        {\n            repeats: 2,\n            aliasing: 1,\n            reuse_pte: 1\n        },\n        {\n            pagesize: '2M',\n        },\n        {\n            repeats: 4,\n            ptes: [\n                {},\n                {\n                    // PTE entry -- set the address + the PPNs\n                    // Something is going wrong with midlevel PTEs\n                    address: [0xdeadbeef0, 0xcafebabe0],\n                },\n                {},\n            ],\n        },\n        {\n            repeats: 4,\n            ptes: [\n                {\n                    // PTE entry -- set the address + the PPNs\n                    address: [0xdeadbeef0, 0xcafebabe0],\n                },\n                {},\n                {},\n            ],\n        },\n    ],\n}\n/*{\n    // comments\n    mode: 39, // Sv3/9\n    // Sample JSON for running test cases\n    memory_size: 0x8000000000,\n    test_cases: [\n        {\n            // If nothing is specified, just randomly create simple cases\n            repeats: 100,\n        },\n        {\n            repeats: 1, // How many times to make the test case\n            // Probabilistic fields:\n            same_va_pa: 0.05,\n            reuse_pte: 0.05,\n            aliasing: 0.05,\n            // VA and PA take the data\n            va: 0x9930_1234,\n            // pa: 0x1423_1234,\n            ptes: [\n                {},\n                {\n                    // PTE entry -- set the address + the PPNs\n                    address: 0x7b5f38ef3fb8,\n                    ppns: [null, 0x119, null],\n                },\n                {\n                    attributes: {\n                        // Set the flags (RSW, DAGUXWRV) probabilistically on the PTE\n                        g: 0.5, // Float for probabilities\n                        u: 1, // 0 - 1 aren't probabilities\n                        x: 0.5, // Float for probabilities\n                        r: 1, // 0 - 1 aren't probabilities\n                        w: 0, // 0 - 1 aren't probabilities\n                    },\n                },\n            ],\n        },\n        {\n            repeats: 100, // How many times to make the test case\n            // Probabilistic fields:\n            same_va_pa: 0.1,\n            reuse_pte: 0.1,\n            aliasing: 0.1,\n            // VA and PA take the data\n            // va: 0x9930_1234,\n            // pa: 0x1423_1234,\n            ptes: [\n                {},\n                {\n                    // PTE entry -- set the address + the PPNs\n                    address: 0x7b5f38ef3fb8,\n                    ppns: [null, 0x119, null],\n                },\n                {\n                    attributes: {\n                        // Set the flags (RSW, DAGUXWRV) probabilistically on the PTE\n                        g: 0.5, // Float for probabilities\n                        u: 1, // 0 - 1 aren't probabilities\n                        x: 0.5, // Float for probabilities\n                        r: 1, // 0 - 1 aren't probabilities\n                        w: 0, // 0 - 1 aren't probabilities\n                    },\n                },\n            ],\n        },\n        {\n            repeats: 1, // How many times to make the test case\n            // Probabilistic fields:\n            // same_va_pa: 0.1,\n            // reuse_pte: 0.1,\n            // aliasing: 0.1,\n            // VA and PA take the data\n            // va: 0x9930_1234,\n            // pa: 0x1423_1234,\n            ptes: [\n                {},\n                {\n                    // PTE entry -- set the address + the PPNs\n                    ppns: [null, 0x119, null],\n                    // address: [0xcafe_babe_0, 0xdead_beef_0], // an array where a number should be = randomly choose a value from the array\n                },\n                {\n                    attributes: {\n                        // Set the flags (RSW, DAGUXWRV) probabilistically on the PTE\n                        g: 0.5, // Float for probabilities\n                        u: 1, // 0 - 1 aren't probabilities\n                        x: 0.5, // Float for probabilities\n                        r: 1, // 0 - 1 aren't probabilities\n                        w: 0, // 0 - 1 aren't probabilities\n                    },\n                },\n            ],\n        },\n    ],\n}\n/*\n    ],\n}\n*/\n"}, {"name": "sample2", "data": "{\n    // comments\n    mode: 48, // Sv48\n    // Sample JSON for running test cases\n    memory_size: 0x3000000000, // 192 GB\n    lower_bound: 0x2000000000, // Start addresses from at least here\n    test_cases: [\n        {\n            repeats: 4, // How many times to make this kind of test case\n            ptes: [\n                {},\n                {},\n                {},\n                {\n                    attributes: {\n                        // Set the flags (RSW, DAGUXWRV) probabilistically on the PTE\n                        G: 0.5, // Float for probabilities\n                        U: 1, // 0 - 1 set/unset flags\n                        X: 0.5, // Float for probabilities\n                        W: 0, // 0 - 1 set/unset flags\n                        R: 1, // 0 - 1 set/unset flags\n                    },\n                },\n            ],\n        },\n        {\n            repeats: 5,\n            reuse_pte: 0.5, // Reuse a previously defined PTE 50% of the time\n        },\n        {\n            reuse_satp: true,\n            repeats: 4,\n            ptes: [\n                {},\n                {\n                    // PTE entry -- set the address + the PPNs\n                    address: 0xcafebabe0,\n                },\n                {},\n            ],\n        },\n        {\n            repeats: 4,\n            ptes: [\n                {\n                    // PTE entry -- set the address + the PPNs\n                    // If you use a list wehere a number is needed, it'll choose at random\n                    address: [0xdeadbeef0, 0xcafebabe0],\n                },\n                {},\n                {},\n            ],\n        },\n        {\n            repeats: 2,\n            // Specifying an entire path\n            ptes: [\n                { address: 0x00001452876690 },\n                { address: 0x000011fd18ccb8 },\n                { address: 0x000027960d1f80 },\n                { address: 0x0000264afd7c28 },\n            ],\n        },\n        {\n            \"repeats\": 2,\n            // SATP + VA = exact same path\n            \"satp.ppn\": 0xb00ffff000,\n            \"va\": 0xf00fb00f,\n        },\n        {\n            repeats: 40,\n            same_va_pa: 1,\n        },\n        {\n            // Possible to Alias and! do the same VA PA\n            repeats: 2,\n            same_va_pa: 1,\n            aliasing: 1,\n        },\n        {\n            // Same SATP + VA to same page = maps to same physical page\n            \"satp.ppn\": 0xb00ffff000,\n            \"va\": 0xf00ff0000,\n        },\n        {\n            \"satp.ppn\": 0xb00ffff000,\n            \"va\": 0xf00ff0008,\n        },\n        {\n            repeats: 5,\n            pagesize: '512G', // Cases can be set to a different pagesize\n        },\n        {\n            repeats: 5,\n            pagesize: ['512G', '1G', '2M'], // Cases can also be set to randomly choose one from a list\n        }\n    ],\n}\n"}, {"name": "sample_invalid", "data": "{\n    // comments\n    mode: 48, // Sv48\n    // Sample JSON for running test cases\n    // memory_size: 0x9000000000, // 576 GiB\n    // lower_bound: 0x2000000000, // Start addresses from at least here\n    test_cases: [\n        {\n            \"satp.ppn\": 0xcafebabe,\n            va: 0xcafebabe,\n            repeats: 50,\n            pagesize: \"2M\",\n            errors: {\n                p: 0.5,\n                types: [\n                    \"mark_invalid\",\n                    \"write_no_read\",\n                    // \"global_nonglobal\",\n                    \"leaf_as_pointer\",\n                    \"uncleared_superpage\",\n                ],\n                weights: [1,4,2,5]\n            },\n        },\n    ],\n}\n"}, {"name": "sample_page_ranges", "data": "{\n    // comments\n    mode: 48, // Sv48\n    // Sample JSON for running test cases\n    // memory_size: 0x9000000000, // 576 GiB\n    // lower_bound: 0x2000000000, // Start addresses from at least here\n    test_cases: [\n        {\n            \"page_range\": {\n                start: 0x10000,\n                num_pages: 100,\n                // end: 0x4000, // can also be done as area\n                // step: 0x2000, // you can step instead of using the pagesize\n            },\n            \"special\": [\n                {\n                    index: 28,\n                    // Specifying an entire path\n                    ptes: [\n                        { address: 0x00001452876690 },\n                        { address: 0x000011fd18ccb8 },\n                        { address: 0x000027960d1f80 },\n                        { address: 0x0000264afd7c28 },\n                    ],\n                },\n            ],\n            \"satp.ppn\": 0xcafebabe,\n            \"pagesize\": [\"1G\", \"2M\", \"4K\"],\n            // same_va_pa: 1 // This with pagesize mixed will almost certainly cause a failure\n        },\n    ],\n}"}, {"name": "sample_pte_range", "data": "{\n    // comments\n    mode: 48, // Sv48\n    pte_min: 0x50000000,\n    pte_max: 0x50001000,\n    // Sample JSON for running test cases\n    // memory_size: 0x9000000000, // 576 GiB\n    // lower_bound: 0x2000000000, // Start addresses from at least here\n    test_cases: [\n        {\n            repeats: 50,\n            // \"page_range\": {\n            //     start: 0x1000,\n            //     num_pages: 1000,\n            //     // end: 0x4000, // can also be done as area\n            //     // step: 0x2000, // you can step instead of using the pagesize\n            // },\n            // // \"special\": [\n            // //     {\n            // //         index: 28,\n            // //         // Specifying an entire path\n            // //         ptes: [\n            // //             { address: 0x00001452876690 },\n            // //             { address: 0x000011fd18ccb8 },\n            // //             { address: 0x000027960d1f80 },\n            // //             { address: 0x0000264afd7c28 },\n            // //         ],\n            // //     },\n            // ],\n            // \"satp.ppn\": 0xcafebabe,\n            // \"pagesize\": [\"1G\", \"2M\", \"4K\"],\n            // same_va_pa: 1 // This with pagesize mixed will almost certainly cause a failure\n        },\n    ],\n}\n"}, {"name": "simpler_sample", "data": "{\n    // comments\n    mode: 48, // Sv48\n    // Sample JSON for running test cases\n    memory_size: 0x3000000000, // 192 GB\n    test_cases: [\n        {\n            repeats: 4,\n            ptes: [\n                {},\n                {},\n                {},\n                {\n                    attributes: {\n                        // Set the flags (RSW, DAGUXWRV) probabilistically on the PTE\n                        G: 0.5, // Float for probabilities\n                        U: 1, // 0 - 1 aren't probabilities\n                        X: 0.5, // Float for probabilities\n                        W: 0, // 0 - 1 aren't probabilities\n                        R: 1, // 0 - 1 aren't probabilities\n                    },\n                },\n            ],\n        },\n        {\n            repeats: 4,\n            ptes: [\n                {},\n                {\n                    // PTE entry -- set the address + the PPNs\n                    // Something is going wrong with midlevel PTEs\n                    address: 0xcafebabe0,\n                },\n                {},\n            ],\n        },\n        {\n            repeats: 4,\n            ptes: [\n                {\n                    // PTE entry -- set the address + the PPNs\n                    // If you use a list wehere a jumber is needed, it'll choose at random\n                    address: [0xdeadbeef0, 0xcafebabe0],\n                },\n                {},\n                {},\n            ],\n        },\n        {\n            repeats: 2,\n            // Specifying an entire path\n            ptes: [\n                { address: 0x00001452876690 },\n                { address: 0x000011fd18ccb8 },\n                { address: 0x000027960d1f80 },\n                { address: 0x0000264afd7c28 },\n            ],\n        },\n        {\n            repeats: 2,\n            // SATP + VA = exact same path\n            satp: { ppn: 0xb00ffff000 },\n            va: 0xf00fb00f,\n        },\n        {\n            repeats: 4,\n            same_va_pa: 1,\n        },\n        {\n            repeats: 2,\n            same_va_pa: 1,\n            aliasing: 1,\n        },\n        {\n            satp: { ppn: 0xb00ffff000 },\n            va: 0xf00ff0000,\n        },\n        {\n            satp: { ppn: 0xb00ffff000 },\n            va: 0xf00ff0008,\n        },\n        {\n            repeats: 5,\n            reuse_pte: 1,\n        },\n    ],\n}\n"}]