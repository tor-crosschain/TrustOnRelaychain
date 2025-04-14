import os, sys
import json
import math
from brokenaxes import brokenaxes
from matplotlib import pyplot as plt

sys.path.insert(0, os.path.abspath("."))

OUTPUT_FILE = "./bcr/result/data_{name}.json"
IMAGE_PATH = "./bcr/images/"
output_path = lambda x: os.path.join(os.path.abspath(IMAGE_PATH), x)
data_filter_num = lambda data: list(
    map(lambda x: math.log(x[1], 2), filter(lambda x: x[0] % 20 == 0, enumerate(data)))
)
data_filter_num_group = lambda data: list(
    filter(lambda x: x[0] % 20 == 0, enumerate(data))
)
average = lambda x: sum(x) / len(x)


class Data:
    def __init__(self) -> None:
        self.UpdateNull = self.__read_data("UpdateNull")
        self.BCRUpdate = self.__read_data("BCRUpdate")
        self.BCRUpdateOpt = self.__read_data("BCRUpdateOpt")
        self.UpdateByLeaves = self.__read_data("UpdateByLeaves")
        self.UpdateByTree = self.__read_data("UpdateByTree")

    def __read_data(self, name: str) -> dict:
        return json.load(
            fp=open(OUTPUT_FILE.format(name=name), "r"),
        )


def essay_gas():

    SMALL_SIZE = 20
    MEDIUM_SIZE = 26
    plt.rcParams["font.weight"] = "bold"
    plt.rcParams["axes.labelweight"] = "bold"
    plt.rc("font", size=MEDIUM_SIZE)  # controls default text sizes
    plt.rc("axes", labelsize=MEDIUM_SIZE)  # fontsize of the x and y labels
    plt.rc("xtick", labelsize=SMALL_SIZE)  # fontsize of the tick labels
    plt.rc("ytick", labelsize=SMALL_SIZE)  # fontsize of the tick labels
    plt.rc("legend", fontsize=SMALL_SIZE)  # legend fontsize
    plt.rc("figure", titlesize=MEDIUM_SIZE)  # fontsize of the figure title
    linewidth = 5
    mew = 3
    ms = 3

    data = Data()
    fig = plt.figure(figsize=(9, 7))
    # fig.suptitle("gas used", fontsize=16)
    fig.tight_layout()

    key = "gasUseds"
    y1 = data_filter_num(data.BCRUpdate[key])
    y2 = data_filter_num(data.BCRUpdateOpt[key])
    y3 = data_filter_num(data.UpdateByTree[key])
    y4 = data_filter_num(data.UpdateByLeaves[key])
    y5 = data_filter_num(data.UpdateNull[key])

    plt.title(f"gas costs")
    plt.xlabel("index of update operation")
    plt.ylabel(r"$\mathrm{log_2 (gas)}$")

    # ax.plot(y1, label="BCRUpdate", marker="s")
    plt.plot(y2, label=r"$A^{u}_{BCR}$", linewidth=linewidth, mew=mew, ms=ms)
    plt.plot(y3, label="UpdateByTree", linewidth=linewidth, mew=mew, ms=ms)
    plt.plot(y4, label="UpdateByLeaves", linewidth=linewidth, mew=mew, ms=ms)
    plt.plot(y5, label="UpdateNull", linewidth=linewidth, mew=mew, ms=ms)
    plt.ylim(17.5, 20.5)
    plt.legend()
    fig.savefig(output_path("output_essay_gas.jpg"))


def gas():
    data = Data()
    ncol = 1
    nrow = 1
    index = 0
    total_width, n = 0.2, 2
    width = total_width / n
    width = width / 3 * 2
    fig = plt.figure(figsize=(ncol * 10, nrow * 10))
    # fig.suptitle("gas used", fontsize=16)
    fig.tight_layout()
    plt.subplots_adjust(
        left=None, bottom=None, right=None, top=None, wspace=0.3, hspace=0.5
    )

    key = "gasUseds"
    y1 = data_filter_num(data.BCRUpdate[key])
    y2 = data_filter_num(data.BCRUpdateOpt[key])
    y3 = data_filter_num(data.UpdateByTree[key])
    y4 = data_filter_num(data.UpdateByLeaves[key])
    y5 = data_filter_num(data.UpdateNull[key])

    index += 1
    ax = plt.subplot(
        nrow,
        ncol,
        index,
    )
    ax.set_title(f"gas costs", fontsize=20, pad=20)
    ax.set_xlabel("index of update operation", fontdict={"fontsize": 16})
    ax.set_ylabel(r"$\mathrm{log_2 (gas)}$", fontdict={"fontsize": 16})
    plt.subplots_adjust(
        left=None, bottom=None, right=None, top=None, wspace=None, hspace=0.5
    )

    maxindex = len(y1)
    # ax.plot(y1, label="BCRUpdate", marker="s")
    ax.plot(y2, label=r"$A^{u}_{BCR}$", marker="^")
    ax.plot(y3, label="UpdateByTree", marker="*")
    ax.plot(y4, label="UpdateByLeaves", marker="D")
    ax.plot(y5, label="UpdateNull", marker=".")
    ax.set_ylim(17.5, 20.5)

    # # arrow for y5
    # arrow_x_length = 0.5
    # arrow_y_length = 1.0
    # xy, xytext = (
    #     (
    #         maxindex // 2,
    #         y5[maxindex // 2] - 0.2,
    #     ),
    #     (
    #         maxindex // 2 + arrow_x_length,
    #         y5[maxindex // 2] - arrow_y_length,
    #     ),
    # )
    # ax.annotate(
    #     f"avg(UBN) = {average(data.UpdateNull[key]):.2f}",
    #     xy=xy,
    #     xycoords="data",
    #     # xytext=(0.36, 0.68),
    #     # textcoords="axes fraction",
    #     xytext=xytext,
    #     # textcoords="offset points",
    #     arrowprops=dict(facecolor="red", shrink=0.05),
    #     # horizontalalignment="right",
    #     # verticalalignment="top",
    #     fontsize=16,
    # )

    # # arrow for y4
    # arrow_x_length = 0.5
    # arrow_y_length = 0.5
    # xy, xytext = (
    #     (
    #         maxindex // 2,
    #         y4[maxindex // 2],
    #     ),
    #     (
    #         maxindex // 2 - arrow_x_length,
    #         y4[maxindex // 2] + arrow_y_length,
    #     ),
    # )
    # ax.annotate(
    #     f"avg(UBL) = {average(data.UpdateByLeaves[key]):.2f}",
    #     xy=xy,
    #     xycoords="data",
    #     # xytext=(0.36, 0.68),
    #     # textcoords="axes fraction",
    #     xytext=xytext,
    #     # textcoords="offset points",
    #     arrowprops=dict(facecolor="red", shrink=0.05),
    #     horizontalalignment="right",
    #     verticalalignment="top",
    #     fontsize=16,
    # )

    # # arrow for y3
    # arrow_x_length = 0.5
    # arrow_y_length = 0.8
    # xy, xytext = (
    #     (
    #         maxindex // 2,
    #         y3[maxindex // 2] + 0.2,
    #     ),
    #     (
    #         maxindex // 2 + arrow_x_length,
    #         y3[maxindex // 2] + arrow_y_length,
    #     ),
    # )
    # ax.annotate(
    #     f"avg(UBT) = {average(data.UpdateByTree[key]):.2f}",
    #     xy=xy,
    #     xycoords="data",
    #     # xytext=(0.36, 0.68),
    #     # textcoords="axes fraction",
    #     xytext=xytext,
    #     # textcoords="offset points",
    #     arrowprops=dict(facecolor="red", shrink=0.05),
    #     # horizontalalignment="right",
    #     # verticalalignment="top",
    #     fontsize=16,
    # )

    # # arrow for y2
    # arrow_x_length = 0.5
    # arrow_y_length = 1.0
    # xy, xytext = (
    #     (
    #         maxindex // 2,
    #         y2[maxindex // 2] - 0.2,
    #     ),
    #     (
    #         maxindex // 2 + arrow_x_length,
    #         y2[maxindex // 2] - arrow_y_length,
    #     ),
    # )
    # ax.annotate(
    #     f"avg(BUO) = {average(data.BCRUpdateOpt[key]):.2f}",
    #     xy=xy,
    #     xycoords="data",
    #     # xytext=(0.36, 0.68),
    #     # textcoords="axes fraction",
    #     xytext=xytext,
    #     # textcoords="offset points",
    #     arrowprops=dict(facecolor="red", shrink=0.05),
    #     # horizontalalignment="right",
    #     # verticalalignment="top",
    #     fontsize=16,
    # )

    ax.legend(fontsize=16)
    fig.savefig(output_path("output_essay_gas.jpg"))


def essay_dur():

    SMALL_SIZE = 20
    MEDIUM_SIZE = 26
    plt.rcParams["font.weight"] = "bold"
    plt.rcParams["axes.labelweight"] = "bold"
    plt.rc("font", size=MEDIUM_SIZE)  # controls default text sizes
    plt.rc("axes", labelsize=MEDIUM_SIZE)  # fontsize of the x and y labels
    plt.rc("xtick", labelsize=SMALL_SIZE)  # fontsize of the tick labels
    plt.rc("ytick", labelsize=SMALL_SIZE)  # fontsize of the tick labels
    plt.rc("legend", fontsize=SMALL_SIZE)  # legend fontsize
    plt.rc("figure", titlesize=MEDIUM_SIZE)  # fontsize of the figure title
    linewidth = 5
    mew = 3
    ms = 3

    data = Data()
    fig = plt.figure(figsize=(9, 7))
    fig.tight_layout()

    key = "durs"
    y1 = data_filter_num(data.BCRUpdate[key])
    y2 = data_filter_num(data.BCRUpdateOpt[key])
    y3 = data_filter_num(data.UpdateByTree[key])
    y4 = data_filter_num(data.UpdateByLeaves[key])
    y5 = data_filter_num(data.UpdateNull[key])

    plt.title(f"CPU execution time")
    plt.xlabel("index of update operation")
    plt.ylabel(r"$\mathrm{log_2 (dur) \cdot ns^{-1}}$")

    plt.plot(y2, label=r"$A^{u}_{BCR}$", linewidth=linewidth, mew=mew, ms=ms)
    plt.plot(y3, label="UpdateByTree", linewidth=linewidth, mew=mew, ms=ms)
    plt.plot(y4, label="UpdateByLeaves", linewidth=linewidth, mew=mew, ms=ms)
    plt.plot(y5, label="UpdateNull", linewidth=linewidth, mew=mew, ms=ms)
    plt.ylim(17, 28)

    plt.legend()
    fig.savefig(output_path("output_essay_dur.jpg"))


def dur():
    data = Data()
    ncol = 1
    nrow = 1
    index = 0
    fig = plt.figure(figsize=(ncol * 10, nrow * 10))
    fig.tight_layout()
    plt.subplots_adjust(
        left=None, bottom=None, right=None, top=None, wspace=0.3, hspace=0.5
    )

    key = "durs"
    y1 = data_filter_num(data.BCRUpdate[key])
    y2 = data_filter_num(data.BCRUpdateOpt[key])
    y3 = data_filter_num(data.UpdateByTree[key])
    y4 = data_filter_num(data.UpdateByLeaves[key])
    y5 = data_filter_num(data.UpdateNull[key])

    index += 1
    ax = plt.subplot(
        nrow,
        ncol,
        index,
    )
    ax.set_title(f"CPU execution time", fontdict={"fontsize": 20}, pad=20)
    ax.set_xlabel("index of update operation", fontdict={"fontsize": 16})
    ax.set_ylabel(r"$\mathrm{log_2 (dur) \cdot ns^{-1}}$", fontdict={"fontsize": 16})
    # ax.plot(y1, label="BCRUpdate", marker="s")
    # ax.scatter(list(range(len(y2))), y2, label="BUO(BCRUpdateOpt)", marker="^")
    # ax.scatter(list(range(len(y2))), y3, label="UBT(UpdateByTree)", marker="*")
    # ax.scatter(list(range(len(y2))), y4, label="UBL(UpdateByLeaves)", marker="D")
    # ax.scatter(list(range(len(y2))), y5, label="UBN(UpdateNull)", marker=".")

    ax.plot(y2, label=r"$A^{u}_{BCR}$", marker="^")
    ax.plot(y3, label="UpdateByTree", marker="*")
    ax.plot(y4, label="UpdateByLeaves", marker="D")
    ax.plot(y5, label="UpdateNull", marker=".")
    ax.set_ylim(17, 28)

    maxindex = len(y1)

    # # arrow for y5
    # arrow_x_length = 0.5
    # arrow_y_length = 1
    # xy, xytext = (
    #     (
    #         maxindex // 2,
    #         y5[maxindex // 2] - 0.2,
    #     ),
    #     (
    #         maxindex // 2 + arrow_x_length,
    #         y5[maxindex // 2] - arrow_y_length,
    #     ),
    # )
    # ax.annotate(
    #     f"avg(UBN) = {average(data.UpdateNull[key]):.2f}",
    #     xy=xy,
    #     xycoords="data",
    #     # xytext=(0.36, 0.68),
    #     # textcoords="axes fraction",
    #     xytext=xytext,
    #     # textcoords="offset points",
    #     arrowprops=dict(facecolor="red", shrink=0.05),
    #     horizontalalignment="left",
    #     verticalalignment="bottom",
    #     fontsize=16,
    # )

    # # arrow for y4
    # arrow_x_length = 0.5
    # arrow_y_length = 1
    # xy, xytext = (
    #     (
    #         maxindex // 2,
    #         y4[maxindex // 2] - 0.2,
    #     ),
    #     (
    #         maxindex // 2 + arrow_x_length,
    #         y4[maxindex // 2] - arrow_y_length,
    #     ),
    # )
    # ax.annotate(
    #     f"avg(UBL) = {average(data.UpdateByLeaves[key]):.2f}",
    #     xy=xy,
    #     xycoords="data",
    #     # xytext=(0.36, 0.68),
    #     # textcoords="axes fraction",
    #     xytext=xytext,
    #     # textcoords="offset points",
    #     arrowprops=dict(facecolor="red", shrink=0.05),
    #     horizontalalignment="left",
    #     verticalalignment="bottom",
    #     fontsize=16,
    # )

    # # arrow for y3
    # arrow_x_length = 0.5
    # arrow_y_length = 1
    # xy, xytext = (
    #     (
    #         maxindex // 2,
    #         y3[maxindex // 2] + 0.2,
    #     ),
    #     (
    #         maxindex // 2 + arrow_x_length,
    #         y3[maxindex // 2] + arrow_y_length,
    #     ),
    # )
    # ax.annotate(
    #     f"avg(UBT) = {average(data.UpdateByTree[key]):.2f}",
    #     xy=xy,
    #     xycoords="data",
    #     # xytext=(0.36, 0.68),
    #     # textcoords="axes fraction",
    #     xytext=xytext,
    #     # textcoords="offset points",
    #     arrowprops=dict(facecolor="red", shrink=0.05),
    #     horizontalalignment="center",
    #     # verticalalignment="top",
    #     fontsize=16,
    # )

    # # arrow for y2
    # arrow_x_length = 0.5
    # arrow_y_length = 1.2
    # x0 = maxindex // 2 + 1
    # xy, xytext = (
    #     (
    #         x0,
    #         y2[x0] - 0.2,
    #     ),
    #     (
    #         x0 + arrow_x_length,
    #         y2[x0] - arrow_y_length,
    #     ),
    # )
    # ax.annotate(
    #     f"avg(BUO) = {average(data.BCRUpdateOpt[key]):.2f}",
    #     xy=xy,
    #     xycoords="data",
    #     # xytext=(0.36, 0.68),
    #     # textcoords="axes fraction",
    #     xytext=xytext,
    #     # textcoords="offset points",
    #     arrowprops=dict(facecolor="red", shrink=0.05),
    #     horizontalalignment="center",
    #     # verticalalignment="top",
    #     fontsize=16,
    # )

    ax.legend(fontsize=16)
    fig.savefig(output_path("output_essay_dur.jpg"))


def hashes():
    data = Data()
    ncol = 1
    nrow = 1
    index = 0
    fig = plt.figure(figsize=(ncol * 10, nrow * 10))

    key = "hashesNum"
    y1 = data.BCRUpdate[key]
    y2 = data.BCRUpdateOpt[key]
    y3 = data.UpdateByTree[key]
    y4 = data.UpdateByLeaves[key]
    y5 = data.UpdateNull[key]
    filter_idx = [10, 100, 500, 1000]
    average = lambda x: float(f"{sum(x)/len(x):.2f}")
    filter_hashes = lambda x: [average(x[: i - 1]) for i in filter_idx]

    print(f"BCRUpdateOpt: {filter_hashes(y2)}")
    print(f"UpdateByTree: {filter_hashes(y3)}")
    print(f"UpdateByLeaves: {filter_hashes(y4)}")
    print(f"UpdateNull: {filter_hashes(y5)}")

    """
    画图效果不明显, 遂放弃
    """
    # y1 = data_filter_num_group(data.BCRUpdate[key])
    # y2 = data_filter_num_group(data.BCRUpdateOpt[key])
    # y3 = data_filter_num_group(data.UpdateByTree[key])
    # y4 = data_filter_num_group(data.UpdateByLeaves[key])
    # y5 = data_filter_num_group(data.UpdateNull[key])
    # bax = brokenaxes(ylims=((0, 15), (990, 1000)))
    # bax.set_title(
    #     f"number of hashes stored in different update algorithms",
    #     fontdict={"fontsize": 20},
    #     pad=20,
    # )
    # bax.set_xlabel("index of update operation", fontdict={"fontsize": 16})
    # bax.set_ylabel(r"$\mathrm{log_2 (dur) \cdot ns^{-1}}$", fontdict={"fontsize": 16})
    # bax.plot(y2, label="BUO(BCRUpdateOpt)", marker="^")
    # bax.plot(y3, label="UBT(UpdateByTree)", marker="*")
    # bax.plot(y4, label="UBL(UpdateByLeaves)", marker="D")
    # bax.plot(y5, label="UBN(UpdateNull)", marker=".")

    # # bax.legend(fontsize=16)
    # fig.savefig(output_path("output_hashes.jpg"))


if __name__ == "__main__":
    essay_gas()
    essay_dur()
    # gas()
    # dur()
    # hashes()
