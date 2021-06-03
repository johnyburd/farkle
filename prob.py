from math import remainder
from os import rename
from random import randint
from collections import Counter, defaultdict
from datetime import datetime
from multiprocessing import Pool
from itertools import chain, combinations

from typing import List, Tuple

farkle_chance = {
    1: 0.6667,
    2: 0.4448,
    3: 0.2780,
    4: 0.1576,
    5: 0.0774,
    6: 0.0233,
}


# expected value not counting re-rolls or farkles given this number of dice remaining:
six_rolled_exp = {5: 74.97966614992609, 4: 149.97288186030437, 6: 1411.1189052565944, 3: 272.90714913839173, 2: 450.5562440820236, 1: 642.4640322780442}
six_rolled_rem = {5: 0.3614330851757541, 4: 0.3011608412001689, 6: 0.016227420584364934, 3: 0.19170240748928408, 2: 0.09884541047002984, 1: 0.030630835080398103}

one_rolled_exp = {6: 75.04376082799975}
one_rolled_rem = {6: 1.0}

two_rolled_exp = {1: 75.01796583266196, 6: 150.0062818016207}
two_rolled_rem = {1: 0.856765504334324, 6: 0.14323449566567606}

three_rolled_exp = {2: 74.98320809369883, 1: 149.8594561839279, 6: 292.9578009466943}
three_rolled_rem = {2: 0.7154087735506366, 1: 0.23836519182309887, 6: 0.04622603462626459}

four_rolled_exp = {1: 285.93424807766604, 6: 468.41367771619787, 3: 75.01640938008926, 2: 149.9573661273882}
four_rolled_rem = {1: 0.10522241464772873, 6: 0.020900411495291888, 3: 0.582702073736949, 2: 0.2911751001200304}

five_rolled_exp = {4: 74.99620823134525, 3: 150.00157224369957, 2: 278.99574481654173, 1: 459.4877836738766, 6: 645.127284311738}
five_rolled_rem = {4: 0.464562782329711, 3: 0.3099873003848875, 2: 0.15721009508001316, 1: 0.058623484261946274, 6: 0.009616337943442153}

data = {
    1: (one_rolled_exp, one_rolled_rem),
    2: (two_rolled_exp, two_rolled_rem),
    3: (three_rolled_exp, three_rolled_rem),
    4: (four_rolled_exp, four_rolled_rem),
    5: (five_rolled_exp, five_rolled_rem),
    6: (six_rolled_exp, six_rolled_rem)
}

expected_score = {
    1: 154.860, #25,
    2: 92.891, #50,
    3: 104.915, #83.5,
    4: 147.648, #132.631,
    5: 214.566, #203.191,
    6: 417.990, #367.5994,
}

calculated = defaultdict(dict)

def powerset(iterable):
     
    return chain.from_iterable(combinations(iterable, r) for r in range(len(iterable) + 1))
    

def calculated_expected(curr: int, num: int, iterations=0):
    if iterations > 0 and num in calculated and curr in calculated[num]:

        return calculated[num][curr]
    if iterations > 10:
        return 0
    exps, rems = data[num]

    total = 0
    for n in rems.keys():
        total += rems[n] * calculated_expected(curr, n, iterations + 1)
        total += rems[n] * exps[n]

    if iterations == 0:
        return (farkle_chance[num] * -curr) + (total * (1 - farkle_chance[num]))
    calculated[num][curr] = total * (1 - farkle_chance[num])
    return calculated[num][curr]

def collect_rolls(num: int = 6, simulated: bool = False) -> List[int]:
    if simulated:
        return [randint(1, 6) for _ in range(num)]
    rolls = input(f"enter space-separated values of your {num}-dice roll: ").split(' ')
    if len(rolls) != num:
        print("invalid number of rolls, please try again")
        return collect_rolls(num)
    try:
        return [int(r) for r in rolls]
    except ValueError:
        print("invalid input, please try again")
        return collect_rolls(num)


def score_roll(roll: List[int]) -> Tuple[int, List[int]]:
    
    count = Counter(roll)
    options = []
    if any(v == 6 for _, v in count.items()):
        options.append((3000, ()))  # 6 of a kind

    if all(v == 3 for v in count.values()) and len(count) == 2:
        options.append((2500, ()))  # 2 triplets

    if any(v == 5 for _, v in count.items()):
        options.append((2000, [next(k for k, v in count.items() if v != 5)] if len(roll) > 5 else ()))  # 5 of kind

    if 4 in count.values() and 2 in count.values():
        options.append((1500, ()))  # 4 of a kind w/ 2 pair

    if all(v == 2 for v in count.values()) and len(count) == 3:
        options.append((1500, ()))  # 3 pairs

    if all(v == 1 for v in count.values()) and len(count) == 6:
        options.append((1500, ()))  # straight

    four_rem = []
    if any(v == 4 for _, v in count.items()):
        value = next(k for k, v in count.items() if v == 4)
        four_rem = [v for v in roll if v != value]
        options.append((1000, four_rem))  # 4 of a kind

    def ones_n_fives(roll, extra=0):
        ones_n_fives = powerset([r for r in roll if r in (1, 5)])
        for combo in ones_n_fives:
            if len(combo) == 0:
                continue
            rem = roll.copy()
            score = 0
            for i in combo:
                rem.remove(i)
                score += 50 if i == 5 else 100
            options.append((score + extra, rem))

    threes_of_a_kind = [k for k, v in count.items() if v == 3]

    for tripplet in threes_of_a_kind:
        rem = roll.copy()
        for _ in range(3):
            rem.remove(tripplet)
        score = (tripplet * 100) if tripplet != 1 else 300
        options.append((score, rem))

    if threes_of_a_kind:
        ones_n_fives(rem, score)
    if four_rem:
        ones_n_fives(four_rem, 1000)
    ones_n_fives(roll)
        
    return options

def analyze_roll(rolls, total = 0):
    print(f"roll: {rolls}")
    options = score_roll(rolls)

    #print(f"score: {score}, remainder: {remaining}, expected: {calculated_expected(score, len(remaining))}")
    print(f"{'score':<6} {'remainder':<12} {'exp gain':<10} {'exp total':<10}")
    for score, remaining in options:
        len_rem = len(remaining) if len(remaining) != 0 else 6
        expected = calculated_expected(total + score, len_rem)
        #print(f"expceted: {expected}")
        print(f"{score:<6} {','.join(str(c) for c in remaining):<12} {round(expected, 2):<10} {round(expected + score + total, 2):<10}")
    
    try:
        best = options[0]
        best_stop = options[0]
        for o in options:
            len_b = len(best[1]) if len(best[1]) != 0 else 6
            expected = calculated_expected(total + o[0], len(o[1]) if len(o[1]) != 0 else 6)
            # print(total)
            # print(best[0])
            expected_b = calculated_expected(total + best[0], len_b)
            # print(f'expected_b: {expected_b}')

            if expected + o[0] > expected_b + best[0]:
                best = o
                expected_b = calculated_expected(total + best[0], len_b)
                # print(f'nexpected_b: {expected_b}')


            if o[0] > best_stop[0]:
                best_stop = o


        dice = len(best[1]) if len(best[1]) != 0 else 6
        if expected_b > 0: # and best_stop[0] > expected_b + best[0]:
            for r in best[1]:
                rolls.remove(r)
            print(f"Recommend taking {','.join(str(r) for r in rolls)} ({total + best[0]}) and rolling {dice} di{'c' if dice > 1 else ''}e for an expected gain of {expected_b:.1f} and a {farkle_chance[dice] * 100:.1f}% chance of farkling")
            return total + best[0], len(best[1])
        else:
            for r in best_stop[1]:
                rolls.remove(r)
            print(f"Recommend taking {','.join(str(r) for r in rolls)} ({total + best_stop[0]}) and stopping.")
    except IndexError:
        import traceback
        traceback.print_exc()
        print(f'You got: {total}')



def get_total_score(rolls, reroll: bool = False):
    total = 0
    score, remaining = score_roll(rolls)
    total += score
    # print(f"score: {score} remaining: {remaining}")
    while score != 0 and len(remaining) > 0:
        score, remaining = score_roll(remaining)
        total += score
        # print(f"score: {score} remaining: {remaining}")
    # print(f"total: {total}")
    if reroll and len(remaining) == 0:
        score = get_total_score(collect_rolls(6, True))
        return 0 if score == 0 else score + total
    return total

def get_subrolls(rolls):
    dist = Counter()
    scores = Counter()

    options = score_roll(rolls)
    for o in options:
        num_rem = len(o[1]) if len(o[1]) > 0 else 6
        dist[num_rem] += 1
        scores[num_rem] += o[0]

    return {k: v for k, v in scores.items()}, dict(dist)


def farckle_percent(args):
    try:
        i = args[0]
        n = args[1]
        wrong = 0
        for _ in range(n):
            rolls = collect_rolls(i, True)
            if len(score_roll(rolls)) == 0:
                wrong += 1
        return wrong / n
    except Exception:
        import traceback
        traceback.print_exc()

def average(args):
    try:
        i = args[0]
        n = args[1]
        sum = 0
        for _ in range(n):
            rolls = collect_rolls(i, True)
            sum += get_total_score(rolls, True)
        return sum / n
    except Exception:
        import traceback
        traceback.print_exc()

def subrolls(args):
    try:
        i = args[0]
        n = args[1]
        scores = Counter()
        dist = Counter()

        for _ in range(n):
            rolls = collect_rolls(i, True)
            s, d = get_subrolls(rolls)
            scores += s
            dist += d
        return {k: v / dist[k] for k, v in scores.items()}, {k: v / sum(dist.values()) for k, v in dist.items()}
    except Exception:
        import traceback
        traceback.print_exc()

def simulate(n):
    num_procs = 4

    for i in range(1, 7):
        then = datetime.now()
        with Pool(num_procs) as p:
            results = list(filter(None, p.map(average, [(i, n // num_procs) for _ in range(num_procs)])))
        print(f'{n} simulations of {i}-dice rolls took {datetime.now() - then}')
        print(f"average for {i} rolls: {sum(results) / len(results)}")

def sim_farckle(n):
    num_procs = 4

    for i in range(1, 7):
        then = datetime.now()
        with Pool(num_procs) as p:
            results = list(filter(None, p.map(farckle_percent, [(i, n // num_procs) for _ in range(num_procs)])))
        print(f'{n} simulations of {i}-dice rolls took {datetime.now() - then}')
        print(f"average for {i} rolls: {sum(results) / len(results)}")

def sim_sub_rolls(n):
    num_procs = 4

    for i in range(1, 7):
        then = datetime.now()
        with Pool(num_procs) as p:
            results = list(filter(None, p.map(subrolls, [(i, n // num_procs) for _ in range(num_procs)])))
        print(f'{n} simulations of {i}-dice rolls took {datetime.now() - then}')
        print(results)
        #print(f"average for {i} rolls: {sum(results) / len(results)}")


def start(score=0, dice=0):
    if dice == 0:
        try:
            dice = int(input("number of dice to roll: "))
        except ValueError:
            dice = 6
    if score == 0:
        try:
            score = int(input("score so far this round: "))
        except ValueError:
            score = 0
    try:
        score, num = analyze_roll(collect_rolls(dice, False), score)
        i = input("Use recommended? [Y/n]:").lower()
        if i == '' or i == 'y':
            start(score, num or 6)
    except TypeError:
        pass
if __name__ == '__main__':
    start()
    #print(subrolls((6, 1_000)))
    #print(get_subrolls(collect_rolls(6, True)))
    #roll = collect_rolls(6, True)
    #print(roll)
    #print(get_subrolls(roll))
    #for i in range(1, 7):
    #    print(i)

    #    print(calculated_expected(0, i))

    #    print(subrolls((i, 1_000_000)))

    #print({k: a[0][k] * a[1][k] for k in a[0].keys()})
    #print(score_roll(roll))
    #sim_farckle(1_000_000)

    # simulate(1_000_000)