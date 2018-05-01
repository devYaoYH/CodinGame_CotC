# Free Pasta
I'm fine with people reading my source code and learning from it. In fact, I learn best by reading through some code then cementing my understanding by implementing my own version of the code. But you'll never learn by blatantly copy-pasting another's code...so if there're people in the community who's fine with such an atrocity, it's best to at least encourage them to actively learn by not uploading a full source code here...

I've taken out the main part of the bot - the **BFS search**. Completing the code is easy enough once you get around implementing a BFS function. Looking back, my AI is really *really* simple...there's not that much aside from the BFS lol, rest is heuristic spaghetti which I left in for your consumption :D

A final word of warning...contest code is not gonna be pretty, **enter at your own risk.**

# Post Morterm - Python!

Well...this competition was dominated by C/C++ and Java, probably due to the nature of the problem statement. It is one that suits searching algos well, very much in my opinion like Fantastic Bits on discrete space (and without the physics).

That being said, kudos to my fellow Python comrade @Icebox for sticking it through with Spaghetti ;) and reaching top 50!
### Rough Algo
- Sequential BFS search for each ship (updating between ships) for the next move that results in best-scoring state after 3 moves
- If WAIT, decide whether to FIRE or MINE

That's it! My bot is essentially a bfs with some heuristics layered on top of it.

## Heuristics

1. Decide between running main function or 'sacrifice' option

    - The latter simply tweaks certain scoring factors in the bfs algo by adding a score (distance to highest health ship and vice versa for the highest health ship to move closer to the sacrificial ship)
    - Once the two ships are sufficiently close together and enemy ships are sufficiently far as to not be able to swoop in and steal the dropped barrel, either move into an already existing cannonball/mine or fire one to self-destruct

2. Run bfs for enemy ships (3 moves)
    - Doesn't account for obstacles, more of an approximation of enemy ships' range
    - Based on simulation, predict possible locations enemy will MINE
    - Also adds a score to list of visited locations for my ships to track probability of hit based on enemy ships visiting that cell (something like what @RoboStac did) to determine where to fire upon enemy ships.

3. Predict enemy fires (that will land in <= 2 turns)
    - Sometimes makes my ships run into a mine in front of it thinking that the enemy will shoot at the center...(so it picks the -25 option rather than the -50 one even if the enemy doesn't actually shoot on that turn)
    - Although it breaks occasionally, it keeps my ships moving when the enemy is close and enables them to have greater flexibility to evade enemy fires. So ultimately it was an improvement to my bot's performance.

4. Stopping just short of the final few barrels to ration rum :P
    - If you pick up the last barrel later than your opponent (and have more total rum), you've likely won that game unless your opponent does something cool like having their ships exhibit cooperative behavior to block your ship then shoot it...:O

## BFS + Scoring
Within the bfs function is where most of the magic happens ;) Significantly it's where I teach my ships to *'run into space'*. Future flexibility of movement contributes a portion of the score after rum count and distance to barrels. Basic scoring like +k*1/distTo(barrels), -l*1/distTo(mines) are standard to determine some positional advantage after movement. In addition to those, I threw in an accumulative scoring of **free cells you can travel to** after each move.

- Look ahead at what cells are reachable and weigh cells ahead of you higher than those you'll have to turn to reach.
- Filter out undesirable cells
- Add a score based on how many of these cells exist
- Tuned to be a magnitude lower score than distance scoring so it's more of a tie-breaker (hidden if-else spaghetti inside scoring :P )
- So if barrels are close, distance scoring will outweigh this 'space-finding’ weight, but otherwise, on my way there and after all barrels have been picked up, I take the path I have the greatest degree of freedom on.

For such scoring functions you really have to get a feel of how it is performing by tweaking the constants in it...probably a GA would be able to auto-tune these for you to reach peak performance haha, but it was faster for me to manually tune them as I didn't have ready access to a GA and local arena.

## Optimizations
With python, I could at maximum, simulate ~1k moves before my bot times out...so with 3 ships, I could not move past a search depth of 3 moves into the future (but it was seemingly sufficient). Even 1k moves required me to change some of my code to optimize its execution speed.
Honestly, I’m not even sure these are legitimate optimizations for python, but the following are some things that I changed to make my code work under the time limit...
### Dfs
Initially I went ahead with a dfs search (since I wanted to compare end-states rather than picking the first one that had a barrel in it - you might run into an unavoidable mine/cannonball on your next move with that sort of pathing), but it constantly made my bot timeout even at depth 3 (5^3=125 moves). Apparently **python and recursion don't go so well together**. So I took @DarthPED’s advice from the previous contest and ported over to a bfs algo, and the while loop ran quite smoothly...for a while...
### Bfs
Even with bfs, I took ~10ms per ship for depth 3 o.O pretty surprised at that...python is slow, but shouldn't be *that* slow...So after looking into my algo, this line

```
#Declaring v[23][21][3][6]
v = [[[[False for i in xrange(6)] for j in xrange(3)] for k in xrange(21)] for l in xrange(23)]
```
by itself took ~8ms :O So instead of declaring such a big sparse 4d array, I encoded the current state into an unique int:

```python
#v_state = xxyyso
v_state = int(x*10000)+int(y*100)+int(speed*10)+int(orientation)
```
added it to a list and searched the list when I needed to find out if I've visited the state before (since my search depth wasn't that large, this took significantly less time than declaring a huge array.
### Modifying game state between simulated moves
Something that I learnt playing FB multiplayer >.< Since python passes variables in functions solely by reference, I had to explicitly copy the game state before modifying it to prevent one simulation affecting another inaccurately which resulted in a huge overhead to my bfs. However, as changes to the gamestate between moves aren't really that numerous, using a list to keep track of adjustments to the state between moves was far cheaper. So I had stuff like:

```
if (key in mine_key_list and key not in cur_rem_mines):
```
Once again I encoded grid locations for objects into an int and stored that in an array rather than cloning and mutating a sparse 2d array.
### Precomputing distances and adjacent cell locations
Because I stuck to a 2d array to work with hex coordinates, I had to do some work to access adjacent cells:

```
def cellAhead(loc, orien):
    tmp_bow = (loc[0]+hexAdj[loc[1]%2][orien][0], loc[1]+hexAdj[loc[1]%2][orien][1])
    return tmp_bow
```
So to speed up my algo since many such calls were necessary (to check where the bow and stern of your ship is after certain moves for example), I precomputed a table of the 6 surrounding cells given the central cell location as well as the distances from each cell to another.

These were the significant ‘optimizations’ I did to get my algo running smoothly under time limit in python >.< which probably won't be necessary in another language like C++...As I'm writing this, I came across this [document](https://www.ics.uci.edu/~pattis/ICS-33/lectures/complexitypython.txt) which seems really useful to keep track of algo complexities for python :) - So I should've used a set instead of a list for my lookups since containment is O(1) instead of O(n)

## I'm very much too alive (Epic bugs)

- Bfs that doesn't even work (Silver -> Gold)

    - Instead of using if (v[cur_state]) continue; I carelessly did v[prev_state] instead...getting my bfs stuck on depth 1 all the time

- if (fire.ttt-cur_depth < 2): (Gold -> Legend)
    - My simulation wrongly took cannonballs with a time to target of < 2 as 'hit' :/ so dead cannonballs with a time of 0, -1 etc...would affect my pathing too

- Indexing error (Legend -> Top 50)
    - In order to optimize my code, I precomputed a table of adjacent cells. But to account for stuff like precomp_adjCells[-1][0] I added some offsets to prevent it from breaking the lookup table *which I forgot to add back* when looking up the table in my code lol…

So lesson learnt here: **Fix Bugs > implementing new features**. Maybe when you find yourself scratching your head over why you're not getting that promotion and implementing a ton of new supposedly better features...It's time to take a closer look through your code, refactor it even.

## Thoughts on contest
Really loved the contest this time round, much more freedom than GitC (less mathematically deterministic) but sufficiently constrained (discrete rather than continuous space) so costly boilerplate physics simulation code was unnecessary. This left much more time to add the 'I' into your AI bot :)

The Boss bots were perhaps a little too inaccessible for beginner players and as @marchete pointed out, many couldn't get out of Wood...However, the Gold Boss was incredibly satisfying to finally beat haha and made Legend league that much more legendary :P

It's unfortunate that the kerfuffle with 'code-sharing' happened due to my negligence...I'm more sad about negatively impacting the contest experience than losing my tshirt hmph...I love the challenge of bot coding contests, so much so that any external incentive is a nice bonus to aim for but not my main purpose of participation. Ofc for the next contest you won't be seeing my code on a public repo anymore :sweat_smile:

Thanks to dev team once more for yet another fun contest and to @marchete @mmmd @eulerscheZahl and many others who publically supported me after finding out ppl cloned my bot :slight_smile: :+1:

**EDIT :** I've released a stripped down version of my code for reference.
