# Summary of findings

Online Retail II, a UK online gift retailer that sells mostly to wholesalers. December 2009 to
9 December 2011, £18.9M net revenue, 39,388 orders, 5,851 identified customers.
Full analysis: `notebooks/analysis.ipynb`.

## What the data shows

**1. Revenue held up because existing customers spent more, while new-customer numbers halved.**
Comparing January to November, 2011 revenue was 2.3% higher than 2010, but there were 3.7% fewer
orders. The average order grew 6.2%, from £474 to £504. Over the same months the shop gained
1,511 first-time customers in 2011 against 3,285 in 2010. Part of the 2010 figure is customers who
had bought before the data starts, but every single month of 2011 brought in fewer new customers than
the same month a year earlier.

**2. Two-fifths of the year's revenue arrives in September to November.**
September, October and November made up 39% of January-November revenue in 2010 and 41% in 2011.
November is the peak month in both years (£1.39M and £1.43M).

**3. A quarter of customers bring in 70% of revenue.**
The "Champions" segment (recent and frequent buyers) is 25% of customers and 70% of revenue.
The top 10% of customers alone account for 63%. Three customers in Ireland generate 3.2% of all
revenue.

**4. 823 lapsed customers used to spend a lot.**
The "At risk" segment averaged 5 orders and £1.43M in total, but on average had not ordered for a
year by the end of the data.

**5. Only about one new customer in five orders again the following month.**
The rate was 20% for 2010 cohorts and 23% for 2011 cohorts. Customers first acquired in December
2010 came back least (9%). 28% of all customers ordered only once.

**6. Returns are low overall but concentrated in a few products.**
After removing orders cancelled within a day, returns are 1.9% of gross sales. A few lines are far
higher: the cherry lights range has 28-35% of sales returned, and small fairy cake fridge magnets 53%.

## Recommendations

1. **Find out why new-customer numbers fell in 2011** (marketing spend, channel, pricing, a lost
   marketplace) before planning next year's targets. Current growth depends on a small group of
   existing buyers.
2. **Win back the At-risk segment** with a targeted offer ahead of the September-November peak. If
   one in ten of them came back and spent what they spent over these two years, that is about £140K.
3. **Look after the largest accounts.** With 63% of revenue from the top 10% of customers, losing a
   few of them would show up immediately. A named contact and early access to the autumn range are
   cheap ways to protect them.
4. **Plan stock and staffing around September to November**, when about 40% of revenue arrives.
5. **Check the high-return products** (cherry lights, fridge magnets) for quality or description
   problems with the supplier.
6. **Record a customer ID on every order.** 13.6% of revenue has none, which limits any customer-level
   analysis.

## Limits of this analysis

- December 2011 contains only nine days and is left out of trend and cohort comparisons.
- Customers who bought before December 2009 cannot be told apart from new customers in early 2010.
- Segment boundaries are quintiles, so they describe customers relative to each other, not against a
  fixed target.
