import random
import time
import argparse

class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

def print_list(head):
    vals = []
    curr = head
    while curr:
        vals.append(str(curr.val))
        curr = curr.next
    return " -> ".join(vals)

def copy_list(head):
    if not head: return None
    new_head = ListNode(head.val)
    curr = new_head
    old = head.next
    while old:
        curr.next = ListNode(old.val)
        curr = curr.next
        old = old.next
    return new_head

def iter_linked(head):
    curr = head
    while curr:
        yield curr
        curr = curr.next

def build_list(values):
    dummy = ListNode(0)
    cur = dummy
    for v in values:
        cur.next = ListNode(v)
        cur = cur.next
    return dummy.next

# =====================================================================
# HOD: Insertion Sort
# Stepwise analysis, detail-oriented assembly. O(n^2)
# =====================================================================
def insertion_sort(head):
    if not head or not head.next:
        return head
    
    dummy = ListNode(0)
    dummy.next = head
    p = head.next
    tail = head
    
    while p:
        tmp = dummy.next
        pre = dummy
        
        while tmp != p and p.val >= tmp.val:
            tmp = tmp.next
            pre = pre.next
            
        if tmp == p:
            tail = p
        else:
            tail.next = p.next
            p.next = tmp
            pre.next = p
            
        p = tail.next
        
    return dummy.next

# =====================================================================
# GEBURAH: Selection Sort
# Harsh discrimination, selection of the extreme. O(n^2)
# =====================================================================
def selection_sort(head):
    if not head or not head.next:
        return head
        
    dummy = ListNode(0)
    dummy.next = head
    sorted_tail = dummy
    
    while sorted_tail.next:
        min_node = sorted_tail.next
        p = sorted_tail.next.next
        
        while p:
            if p.val < min_node.val:
                min_node = p
            p = p.next
            
        min_node.val, sorted_tail.next.val = sorted_tail.next.val, min_node.val
        sorted_tail = sorted_tail.next
        
    return dummy.next

# =====================================================================
# CHOKMAH: Quicksort (Node Relinking Version)
# Recursive division, wisdom through separation. O(n log n) average.
# =====================================================================
def quick_sort(head):
    if not head or not head.next:
        return head
        
    pivot = head.val
    less_dummy = ListNode(0)
    equal_dummy = ListNode(0)
    greater_dummy = ListNode(0)
    
    less = less_dummy
    equal = equal_dummy
    greater = greater_dummy
    
    curr = head
    while curr:
        if curr.val < pivot:
            less.next = curr
            less = less.next
        elif curr.val == pivot:
            equal.next = curr
            equal = equal.next
        else:
            greater.next = curr
            greater = greater.next
        curr = curr.next
        
    less.next = equal.next = greater.next = None
    
    sorted_less = quick_sort(less_dummy.next)
    sorted_greater = quick_sort(greater_dummy.next)
    
    res = sorted_less
    if not res:
        res = equal_dummy.next
    else:
        tail = res
        while tail.next:
            tail = tail.next
        tail.next = equal_dummy.next
        
    equal.next = sorted_greater
    return res if res else equal_dummy.next

# =====================================================================
# TIFERETH: Merge Sort
# Harmonious integration, balanced synthesis. O(n log n) guaranteed.
# =====================================================================
def merge_sort(head):
    if not head or not head.next:
        return head
        
    slow = head
    fast = head.next
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        
    mid = slow.next
    slow.next = None
    
    left = merge_sort(head)
    right = merge_sort(mid)
    
    return merge(left, right)

def merge(l1, l2):
    dummy = ListNode(0)
    tail = dummy
    
    while l1 and l2:
        if l1.val < l2.val:
            tail.next = l1
            l1 = l1.next
        else:
            tail.next = l2
            l2 = l2.next
        tail = tail.next
        
    tail.next = l1 if l1 else l2
    return dummy.next

# =====================================================================
# ETHICAL PLACEHOLDERS
# =====================================================================
def shell_sort(_):
    raise NotImplementedError(
        "[!] ETHICAL API: Shell Sort is *unsuitable* for linked lists - the ritual would break."
    )

def heap_sort(_):
    raise NotImplementedError(
        "[!] ETHICAL API: Heap Sort requires random access; forcing it would violate the principle of Non-Reduction."
    )

__all__ = ["ListNode", "insertion_sort", "selection_sort", "quick_sort", "merge_sort", "copy_list", "iter_linked", "build_list", "shell_sort", "heap_sort"]

# =====================================================================
# CLI EXPOSURE
# =====================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sephirotic Sorting Demo - map algorithms to Kabbalistic forces"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed to generate reproducible list")
    parser.add_argument("--algo", choices=["insertion", "selection", "quick", "merge", "shell", "heap"], default="merge", help="Which Sephirotic algorithm to run")
    args = parser.parse_args()

    print("[!] ETHICAL API CAVEAT: This is a symbolic map; the territory is the lived experience.")
    print("[!] There are no 'optimal' algorithms for consciousness. We celebrate all speeds.\n")

    random.seed(args.seed)
    vals = [random.randint(0, 100) for _ in range(12)]
    head = build_list(vals)
    
    print(f"[Original Tohu] {vals}")

    algo_map = {
        "insertion": (insertion_sort, "HOD"),
        "selection": (selection_sort, "GEBURAH"),
        "quick": (quick_sort, "CHOKMAH"),
        "merge": (merge_sort, "TIFERETH"),
        "shell": (shell_sort, "ERROR"),
        "heap": (heap_sort, "ERROR")
    }

    sort_fn, sephira_name = algo_map[args.algo]
    
    start = time.perf_counter()
    sorted_head = sort_fn(head)
    t = time.perf_counter() - start
    
    sorted_vals = [node.val for node in iter_linked(sorted_head)]
    print(f"[{sephira_name} ({args.algo})] Sorted -> {sorted_vals}")
    print(f"Latency: {t:.6f}s")
