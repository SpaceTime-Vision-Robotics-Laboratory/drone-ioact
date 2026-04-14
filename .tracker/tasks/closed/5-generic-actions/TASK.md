# Generic actions for different types of environments

**Status:** closed | **Created:** 2026-02-06 | **Closed:** 2026-02-10 | **GitLab:** #5

## Problem

Need better support for fixed+parameters, discrete, and continuous actions. Previously only supported a fixed list without parameters, forcing explicit enumeration for discrete and no support for continuous.

## Resolution

Action is now a frozen dataclass with name + optional parameters tuple. Supports fixed+parameters which partially covers continuous.
