# Fibonacci VI — complete VI Scripting source

Two parts:
1. **The target VI** — the Fibonacci VI you want to end up with (build it by hand in 5 minutes, or let the scripting generator in Part 2 emit it).
2. **The generator** — a VI Scripting program (block-diagram node sequence) that creates that VI programmatically.

> Why this is source and not a prebuilt `.vi`: a block diagram is a wire/uid graph that only LabVIEW can lay out and validate. These steps map 1:1 onto LabVIEW's VI Server scripting API — paste/drop them in a scripting‑enabled VI (Tools ▸ Options ▸ Environment ▸ *Enable scripting*… or it's on by default in recent LV) and run.

---

## Part 1 — The target Fibonacci VI (plain G)

**Front panel**
- `N` — numeric control, I32 (how many terms)
- `Fibonacci` — numeric **array** indicator, I32

**Block diagram**
```
            ┌─────────────── For Loop (N) ───────────────┐
            │                                             │
   N ───────┤ N                                           │
            │   ┌──────────────┐                          │
 [SR init 0]│a ─┤ a            │                          │
            │   │   Add  ──── sum ─────────────► a' (right SR = old b)   wait: see wiring
 [SR init 1]│b ─┤ b            │                          │
            │   └──────────────┘                          │
            │  a ───────────────────────► (auto-indexed) ─┼──► Fibonacci (array)
            └─────────────────────────────────────────────┘
```

**Exact shift-register wiring (the important bit):**
- Left shift register **A** initialized to **0**, left **B** initialized to **1**.
- Inside: `sum = A + B`  (Add primitive).
- Right shift register for A  ← **B**     (A takes B's old value)
- Right shift register for B  ← **sum**   (B takes A+B)
- Auto-indexed output tunnel ← **A**  → builds the array `[0,1,1,2,3,5,…]`.

For `N = 15` the indicator shows: `0 1 1 2 3 5 8 13 21 34 55 89 144 233 377`.

---

## Part 2 — The VI Scripting generator

This is the node sequence for the **generator VI**'s block diagram. Each numbered
step is one scripting node (Invoke Node / Property Node) wired in order; names are
LabVIEW VI Server methods/properties (class in brackets).

```
# --- create the VI and grab its diagram ---
 1. Open Application Reference            [Application]            -> app
 2. app:New VI                            [Application.New VI]     -> viRef         (template "")
 3. viRef:Front Panel                     [VI.Front Panel]         -> fpRef
 4. viRef:Block Diagram                   [VI.Block Diagram]       -> bdRef

# --- controls / indicator ---
 5. fpRef:Create(Control, "Numeric")      [Panel.Create]           -> ctlN          # the N control
 6. ctlN:Label:Text = "N"                 [Control property]
 7. ctlN:Representation = I32
 8. fpRef:Create(Indicator,"Numeric Array")                        -> indFib        # Fibonacci array
 9. indFib:Label:Text = "Fibonacci"
10. (array element) Representation = I32

# --- the For Loop ---
11. bdRef:Create(Structure, "For Loop")   [Diagram.Create]         -> forLoop
12. forLoop:Left Shift Register:Add        (border method)         -> srA           # shift reg A
13. forLoop:Left Shift Register:Add                                 -> srB           # shift reg B
14. forLoop:Create(Constant, I32=0) and wire to srA (left)   -> 0 init for A
15. forLoop:Create(Constant, I32=1) and wire to srB (left)   -> 1 init for B

# --- Add primitive inside the loop ---
16. forLoop.Diagram:Create(Function,"Add")  [Diagram.Create]       -> addNode       # primResID 1050
     # terminals: x=addNode.Terminal[0], y=addNode.Terminal[1], out=addNode.Terminal[2]

# --- wires (Diagram.Connect Wire between two terminals) ---
17. Connect  srA.LeftTerminal(inside) -> addNode.x
18. Connect  srB.LeftTerminal(inside) -> addNode.y
19. Connect  addNode.out              -> srB.RightTerminal      # B' = A+B
20. Connect  srB.LeftTerminal(inside) -> srA.RightTerminal      # A' = old B
21. Connect  srA.LeftTerminal(inside) -> (loop output tunnel)   # auto-indexed
22. set that output tunnel:  Indexing = TRUE
23. Connect  tunnel -> indFib (array indicator terminal)

# --- wire N to the loop count ---
24. Connect  ctlN.Terminal -> forLoop.Count Terminal (N)

# --- clean up & save ---
25. viRef:Arrange / Clean Up Diagram      [VI.Clean Up Diagram]   (optional)
26. viRef:Save Instrument  path="Fibonacci.vi"   [VI.Save:Instrument]
27. Close Reference  viRef, app
```

### Notes for the real nodes
- **Create method**: in scripting you drop an *Invoke Node* on `bdRef` (a BlockDiagram
  reference) and pick **Create**. Its `Style` enum picks Control/Indicator/Constant/
  Function/Structure; `Class Name`/`Style Name` picks the exact object ("Add",
  "For Loop", "Numeric").
- **Shift registers**: with the For Loop reference, use the **Add Shift Register**
  method (or drop via the border). Each returns left+right terminal refs.
- **Wiring**: use `BlockDiagram:Connect Wire` (Invoke Node) between two terminal
  references; LabVIEW routes the wire.
- **Count terminal**: `ForLoop:Count Terminal` property gives the `N` terminal.
- Everything above is standard, documented VI Server scripting — exact member names
  can shift slightly between LabVIEW versions, so pick them from the Invoke/Property
  node's dropdown.

### Fastest path if you just want the VI
Building Part 1 by hand is quicker than the generator for a one‑off:
1. New VI → drop a **For Loop**.
2. Right‑click the left border twice → **Add Shift Register** (two of them).
3. Wire constants **0** and **1** to the two left shift registers.
4. Inside: drop **Add**; wire SR‑A and SR‑B into it.
5. Add out → right SR‑B;  SR‑A(left) → right SR‑A? No — SR‑B(left) → right SR‑A.
6. SR‑A(left) → right loop tunnel; right‑click tunnel → **Enable Indexing**.
7. Tunnel → **Fibonacci** array indicator; wire **N** to the loop count **N**.
8. Save as `Fibonacci.vi`.
```
0 1 1 2 3 5 8 13 21 34 55 89 144 233 377   (N = 15)
```
