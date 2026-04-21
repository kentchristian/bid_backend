import uuid


DEFAULT_TRANSACTION_GROUP_SIZES = (5, 10, 20)


def parse_transaction_group_sizes(raw_value):
    if raw_value is None:
        return DEFAULT_TRANSACTION_GROUP_SIZES

    sizes = []
    for chunk in str(raw_value).split(","):
        value = chunk.strip()
        if not value:
            continue
        size = int(value)
        if size <= 0:
            raise ValueError("Transaction group sizes must be positive integers.")
        sizes.append(size)

    if not sizes:
        raise ValueError("Provide at least one transaction group size.")

    return tuple(sorted(set(sizes)))


def assign_transaction_ids(sales, rng, group_sizes):
    if not sales:
        return sales

    ordered_sales = sorted(sales, key=lambda sale: sale.sold_at)
    pointer = 0

    while pointer < len(ordered_sales):
        remaining = len(ordered_sales) - pointer
        valid_sizes = [size for size in group_sizes if size <= remaining]
        group_size = rng.choice(valid_sizes) if valid_sizes else remaining
        transaction_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"

        for sale in ordered_sales[pointer : pointer + group_size]:
            sale.transaction_id = transaction_id

        pointer += group_size

    return ordered_sales
