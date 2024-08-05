import json
from matplotlib import pyplot as plt



def gas_cost():
    aor_5_1000 = json.load(open("info/aor/blockchains_aor_5/1000/output.ignore.json", 'r'))
    aor_5_100 = json.load(open("info/aor/blockchains_aor_5/100/output.ignore.json", 'r'))
    aor_10_1000 = json.load(open("info/aor/blockchains_aor_10/1000/output.ignore.json", 'r'))
    aor_10_100 = json.load(open("info/aor/blockchains_aor_10/100/output.ignore.json", 'r'))

    nor_5_1000 = json.load(open("info/nor/blockchains_nor_5/1000/output.ignore.json", 'r'))
    nor_5_100 = json.load(open("info/nor/blockchains_nor_5/100/output.ignore.json", 'r'))
    nor_10_1000 = json.load(open("info/nor/blockchains_nor_10/1000/output.ignore.json", 'r'))
    nor_10_100 = json.load(open("info/nor/blockchains_nor_10/100/output.ignore.json", 'r'))

    tor_5_1000 = json.load(open("info/tor/blockchains_tor_5/1000/output.ignore.json", 'r'))
    tor_5_100 = json.load(open("info/tor/blockchains_tor_5/100/output.ignore.json", 'r'))
    tor_10_1000 = json.load(open("info/tor/blockchains_tor_10/1000/output.ignore.json", 'r'))
    tor_10_100 = json.load(open("info/tor/blockchains_tor_10/1000/output.ignore.json", 'r'))


    ncol = 2
    nrow = 1
    index = 0
    fig = plt.figure(figsize=(13, 6))
    # fig = plt.figure()
    fig.suptitle("realistic gas cost on source/target chains", fontsize=16)
    fig.tight_layout()
    plt.subplots_adjust(
        left=None, bottom=None, right=None, top=None, wspace=0.3, hspace=0.5
    )

    total_width, n = 0.2, 3
    width = total_width / n
    width = width / 3 * 2

    xxx = [0.2, 0.4]
    yy1_nor = [nor_5_100['crossSend'], nor_5_1000['crossSend']]
    yy1_aor = [aor_5_100['crossSend'], aor_5_1000['crossSend']]
    yy1_tor = [tor_5_100['crossSendToR'], tor_5_1000['crossSendToR']]

    yy2_nor = [nor_5_100['crossReceiveFromPara'], nor_5_1000['crossReceiveFromPara']]
    yy2_aor = [aor_5_100['crossReceiveFromRelay'], aor_5_1000['crossReceiveFromRelay']]
    yy2_tor = [tor_5_100['crossReceiveFromParaToR'], tor_5_1000['crossReceiveFromParaToR']]
    

    index += 1
    ax = plt.subplot(
        nrow,
        ncol,
        index,
    )
    ax.set_title(f"paranum={5}")
    ax.set_xlabel("ratio")
    ax.set_ylabel("tx number")
    # ax.set_ylim(ymin=0, ymax=160)
    ax.bar(
        [i - width for i in xxx],
        # xxx,
        yy1_nor,
        width=width,
        label="NoR-max",
        color="white",
        edgecolor="blue",
        hatch="....",
    )
    ax.bar(
        # [i + width / 2 for i in xxx],
        xxx,
        yy1_aor,
        width=width,
        label="AoR-max",
        color="white",
        edgecolor="orange",
        hatch="////",
    )
    ax.bar(
        [i + width for i in xxx],
        # xxx,
        yy1_tor,
        width=width,
        label="ToR-max",
        color="white",
        edgecolor="red",
        hatch="////",
    )
    
    ax.set_xticks(xxx, ['100', '1000'])
    # yticks = list(range(50000,450000,50000))
    yticks = list(range(100000,1100000,100000))
    yticks_text = [ f"{y//1000}k" for y in yticks]
    ax.set_yticks(yticks, yticks_text)


    index += 1
    ax = plt.subplot(
        nrow,
        ncol,
        index,
    )
    ax.set_title(f"paranum={10}")
    ax.set_xlabel("ratio")
    ax.set_ylabel("tx number")
    # ax.set_ylim(ymin=0, ymax=160)
    ax.bar(
        [i - width for i in xxx],
        # xxx,
        yy2_nor,
        width=width,
        label="NoR-max",
        color="white",
        edgecolor="blue",
        hatch="....",
    )
    ax.bar(
        # [i + width / 2 for i in xxx],
        xxx,
        yy2_aor,
        width=width,
        label="AoR-max",
        color="white",
        edgecolor="orange",
        hatch="////",
    )
    ax.bar(
        [i + width for i in xxx],
        # xxx,
        yy2_tor,
        width=width,
        label="ToR-max",
        color="white",
        edgecolor="red",
        hatch="////",
    )
    
    ax.set_xticks(xxx, ['100', '1000'])
    yticks = list(range(100000,1100000,100000))
    yticks_text = [ f"{y//1000}k" for y in yticks]
    ax.set_yticks(yticks, yticks_text)
    



    lines, labels = fig.axes[-1].get_legend_handles_labels()
    fig.legend(lines, labels, loc="upper left")
    fig.savefig("figure/hi.jpg")

def gas_cost_only_pn():
    aor_2_1000 = json.load(open("info/aor/blockchains_aor_2/1000/output.ignore.json", 'r'))
    aor_5_1000 = json.load(open("info/aor/blockchains_aor_5/1000/output.ignore.json", 'r'))
    aor_7_1000 = json.load(open("info/aor/blockchains_aor_7/1000/output.ignore.json", 'r'))
    aor_10_1000 = json.load(open("info/aor/blockchains_aor_10/1000/output.ignore.json", 'r'))

    nor_2_1000 = json.load(open("info/nor/blockchains_nor_2/1000/output.ignore.json", 'r'))
    nor_5_1000 = json.load(open("info/nor/blockchains_nor_5/1000/output.ignore.json", 'r'))
    nor_7_1000 = json.load(open("info/nor/blockchains_nor_7/1000/output.ignore.json", 'r'))
    nor_10_1000 = json.load(open("info/nor/blockchains_nor_10/1000/output.ignore.json", 'r'))

    tor_2_1000 = json.load(open("info/tor/blockchains_tor_2/1000/output.ignore.json", 'r'))
    tor_5_1000 = json.load(open("info/tor/blockchains_tor_5/1000/output.ignore.json", 'r'))
    tor_7_1000 = json.load(open("info/tor/blockchains_tor_7/1000/output.ignore.json", 'r'))
    tor_10_1000 = json.load(open("info/tor/blockchains_tor_10/1000/output.ignore.json", 'r'))


    ncol = 2
    nrow = 1
    index = 0
    fig = plt.figure(figsize=(13, 6))
    # fig = plt.figure()
    fig.suptitle("realistic gas cost on source/target chains", fontsize=16)
    fig.tight_layout()
    plt.subplots_adjust(
        left=None, bottom=None, right=None, top=None, wspace=0.3, hspace=0.5
    )

    total_width, n = 0.2, 3
    width = total_width / n
    width = width / 3 * 2

    xxx = [0.2, 0.4, 0.6, 0.8]
    yy1_nor = [nor_2_1000['crossSend'], nor_5_1000['crossSend'], nor_7_1000['crossSend'], nor_10_1000['crossSend']]
    yy1_aor = [aor_2_1000['crossSend'], aor_5_1000['crossSend'], aor_7_1000['crossSend'], aor_10_1000['crossSend']]
    yy1_tor = [tor_2_1000['crossSendToR'], tor_5_1000['crossSendToR'], tor_7_1000['crossSendToR'], tor_10_1000['crossSendToR']]

    yy2_nor = [nor_2_1000['crossReceiveFromPara'], nor_5_1000['crossReceiveFromPara'], nor_7_1000['crossReceiveFromPara'], nor_10_1000['crossReceiveFromPara']]
    yy2_aor = [aor_2_1000['crossReceiveFromRelay'], aor_5_1000['crossReceiveFromRelay'], aor_7_1000['crossReceiveFromRelay'], aor_10_1000['crossReceiveFromRelay']]
    yy2_tor = [tor_2_1000['crossReceiveFromParaToR'], tor_5_1000['crossReceiveFromParaToR'], tor_7_1000['crossReceiveFromParaToR'], tor_10_1000['crossReceiveFromParaToR']]
    

    index += 1
    ax = plt.subplot(
        nrow,
        ncol,
        index,
    )
    ax.set_title(f"paranum={5}")
    ax.set_xlabel("ratio")
    ax.set_ylabel("tx number")
    # ax.set_ylim(ymin=0, ymax=160)
    ax.bar(
        [i - width for i in xxx],
        # xxx,
        yy1_nor,
        width=width,
        label="NoR-max",
        color="white",
        edgecolor="blue",
        hatch="....",
    )
    ax.bar(
        # [i + width / 2 for i in xxx],
        xxx,
        yy1_aor,
        width=width,
        label="AoR-max",
        color="white",
        edgecolor="orange",
        hatch="////",
    )
    ax.bar(
        [i + width for i in xxx],
        # xxx,
        yy1_tor,
        width=width,
        label="ToR-max",
        color="white",
        edgecolor="red",
        hatch="////",
    )
    
    ax.set_xticks(xxx, ['2', '5', '7', '10'])
    # yticks = list(range(100000,1100000,100000))
    # yticks_text = [ f"{y//1000}k" for y in yticks]
    # ax.set_yticks(yticks, yticks_text)


    index += 1
    ax = plt.subplot(
        nrow,
        ncol,
        index,
    )
    ax.set_title(f"paranum={10}")
    ax.set_xlabel("ratio")
    ax.set_ylabel("tx number")
    # ax.set_ylim(ymin=0, ymax=160)
    ax.bar(
        [i - width for i in xxx],
        # xxx,
        yy2_nor,
        width=width,
        label="NoR-max",
        color="white",
        edgecolor="blue",
        hatch="....",
    )
    ax.bar(
        # [i + width / 2 for i in xxx],
        xxx,
        yy2_aor,
        width=width,
        label="AoR-max",
        color="white",
        edgecolor="orange",
        hatch="////",
    )
    ax.bar(
        [i + width for i in xxx],
        # xxx,
        yy2_tor,
        width=width,
        label="ToR-max",
        color="white",
        edgecolor="red",
        hatch="////",
    )
    
    ax.set_xticks(xxx, ['2', '5', '7', '10'])
    # yticks = list(range(100000,1100000,100000))
    # yticks_text = [ f"{y//1000}k" for y in yticks]
    # ax.set_yticks(yticks, yticks_text)
    
    lines, labels = fig.axes[-1].get_legend_handles_labels()
    fig.legend(lines, labels, loc="upper left")
    fig.savefig("figure/hi.jpg")

def gas_cost_only_pn_line():
    aor_2_1000 = json.load(open("info/aor/blockchains_aor_2/1000/output.ignore.json", 'r'))
    aor_5_1000 = json.load(open("info/aor/blockchains_aor_5/1000/output.ignore.json", 'r'))
    aor_7_1000 = json.load(open("info/aor/blockchains_aor_7/1000/output.ignore.json", 'r'))
    aor_10_1000 = json.load(open("info/aor/blockchains_aor_10/1000/output.ignore.json", 'r'))

    nor_2_1000 = json.load(open("info/nor/blockchains_nor_2/1000/output.ignore.json", 'r'))
    nor_5_1000 = json.load(open("info/nor/blockchains_nor_5/1000/output.ignore.json", 'r'))
    nor_7_1000 = json.load(open("info/nor/blockchains_nor_7/1000/output.ignore.json", 'r'))
    nor_10_1000 = json.load(open("info/nor/blockchains_nor_10/1000/output.ignore.json", 'r'))

    tor_2_1000 = json.load(open("info/tor/blockchains_tor_2/1000/output.ignore.json", 'r'))
    tor_5_1000 = json.load(open("info/tor/blockchains_tor_5/1000/output.ignore.json", 'r'))
    tor_7_1000 = json.load(open("info/tor/blockchains_tor_7/1000/output.ignore.json", 'r'))
    tor_10_1000 = json.load(open("info/tor/blockchains_tor_10/1000/output.ignore.json", 'r'))


    ncol = 2
    nrow = 1
    index = 0
    fig = plt.figure(figsize=(13, 6))
    # fig = plt.figure()
    fig.suptitle("realistic gas cost on source/target chains", fontsize=16)
    fig.tight_layout()
    plt.subplots_adjust(
        left=None, bottom=None, right=None, top=None, wspace=0.3, hspace=0.5
    )

    xxx = [0.2, 0.4, 0.6, 0.8]
    yy1_nor = [nor_2_1000['crossSend'], nor_5_1000['crossSend'], nor_7_1000['crossSend'], nor_10_1000['crossSend']]
    yy1_aor = [aor_2_1000['crossSend'], aor_5_1000['crossSend'], aor_7_1000['crossSend'], aor_10_1000['crossSend']]
    yy1_tor = [tor_2_1000['crossSendToR'], tor_5_1000['crossSendToR'], tor_7_1000['crossSendToR'], tor_10_1000['crossSendToR']]

    yy2_nor = [nor_2_1000['crossReceiveFromPara'], nor_5_1000['crossReceiveFromPara'], nor_7_1000['crossReceiveFromPara'], nor_10_1000['crossReceiveFromPara']]
    yy2_aor = [aor_2_1000['crossReceiveFromRelay'], aor_5_1000['crossReceiveFromRelay'], aor_7_1000['crossReceiveFromRelay'], aor_10_1000['crossReceiveFromRelay']]
    yy2_tor = [tor_2_1000['crossReceiveFromParaToR'], tor_5_1000['crossReceiveFromParaToR'], tor_7_1000['crossReceiveFromParaToR'], tor_10_1000['crossReceiveFromParaToR']]

    index += 1
    ax = plt.subplot(
        nrow,
        ncol,
        index,
    )
    ax.set_title(f"on the source chain", fontsize=16)
    ax.set_xlabel("pn", fontsize=16)
    ax.set_ylabel("gas", fontsize=16)
    ax.set_ylim(ymin=50000, ymax=400000)
    ax.tick_params(labelsize=12)
    ax.plot(xxx, yy1_nor, label="NoR", marker="D")
    ax.plot(xxx, yy1_aor, label="AoR", marker="s")
    ax.plot(xxx, yy1_tor, label="ToR", marker="^")

    index += 1
    ax = plt.subplot(
        nrow,
        ncol,
        index,
    )
    ax.set_title(f"on the target chain", fontsize=16)
    ax.set_xlabel("pn", fontsize=16)
    ax.set_ylabel("gas", fontsize=16)
    ax.set_ylim(ymin=0, ymax=1000000)
    ax.tick_params(labelsize=12)
    ax.plot(xxx, yy2_nor, label="NoR", marker="D")
    ax.plot(xxx, yy2_aor, label="AoR", marker="s")
    ax.plot(xxx, yy2_tor, label="ToR", marker="^")

    lines, labels = fig.axes[-1].get_legend_handles_labels()
    fig.legend(lines, labels, loc="upper left", prop={"size": 12})
    fig.savefig("figure/hi.jpg")


if __name__ == "__main__":
    # gas_cost()
    # gas_cost_only_pn()
    gas_cost_only_pn_line()