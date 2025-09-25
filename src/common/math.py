
# round to the nearest int number n in [minValue, maxValue] range, which is n % div == mod % div
def advancedRound(x: float, div: int, mod: int = 0, minValue: int = None, maxValue: int = None) -> int:
    mod = mod % div

    baseValue = round(x)
    remainder = baseValue % div

    if remainder == mod and (minValue is None or baseValue >= minValue) and (maxValue is None or baseValue <= maxValue):
        return baseValue
    
    # Calculate distances to the nearest values that satisfy n % div == mod
    lowerCandidate = baseValue - remainder + mod
    upperCandidate = lowerCandidate + div
    
    # If mod > remainder, we need to check the previous cycle
    if mod > remainder:
        lowerCandidate -= div
        upperCandidate -= div
    
    # Apply range constraints
    candidates = []
    
    # Check lower candidate
    if (minValue is None or lowerCandidate >= minValue) and (maxValue is None or lowerCandidate <= maxValue):
        candidates.append(lowerCandidate)
    
    # Check upper candidate
    if (minValue is None or upperCandidate >= minValue) and (maxValue is None or upperCandidate <= maxValue):
        candidates.append(upperCandidate)
    
    # If no candidates within range, find the closest valid value
    if not candidates:
        # Find all valid values in the range
        if minValue is not None and maxValue is not None:
            for n in range(minValue, maxValue + 1):
                if n % div == mod:
                    candidates.append(n)
        else:
            # Expand search outward from the original candidates
            searchRange = max(div, 10)  # reasonable search limit
            for offset in range(1, searchRange):
                for candidate in [lowerCandidate - div * offset, upperCandidate + div * offset]:
                    if (minValue is None or candidate >= minValue) and (maxValue is None or candidate <= maxValue):
                        candidates.append(candidate)
                        break
                if candidates:
                    break
    
    # Return the candidate closest to x
    if candidates:
        return min(candidates, key = lambda n: abs(x - n))
    else:
        # No valid candidates found - condition is impossible
        rangeStr = ""
        if minValue is not None and maxValue is not None:
            rangeStr = f" in range [{minValue}, {maxValue}]"
        elif minValue is not None:
            rangeStr = f" >= {minValue}"
        elif maxValue is not None:
            rangeStr = f" <= {maxValue}"
        
        raise ValueError(f"No integer{rangeStr} satisfies n % {div} == {mod}")
