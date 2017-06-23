import torch
from torch.autograd import Variable
from pyro.distributions.distribution import Distribution


def _to_one_hot(x, ps):
    # batch_class_raw = Variable(torch.LongTensor(batch_size,1))

    batch_size = x.size(0)
    classes = ps.size(1)
    # create an empty array for one-hots
    batch_one_hot = torch.zeros(batch_size, classes)

    # this operation writes ones where needed
    batch_one_hot.scatter_(1, x.data.view(-1, 1), 1)

    # this operation turns the one hot tensor again into a Variable
    return Variable(batch_one_hot)


class Categorical(Distribution):
    """
    Categorical is a specialized version of multinomial where n = 1
    """

    def __init__(self, ps, one_hot=True, batch_size=1, *args, **kwargs):
        """
        Constructor.
        """
        if ps.dim() == 1:
            self.ps = ps.unsqueeze(0)
        elif batch_size > 1:
            self.ps = ps.unsqueeze(0).expand(batch_size, 0)
        else:
            self.ps = ps
        # self.n = Variable(torch.Tensor([1])).expand_as(ps)
        # self.batch_size = batch_size
        self.one_hot = one_hot
        # self.dist = Multinomial(self.ps, self.n, self.batch_size)
        super(Categorical, self).__init__(batch_size=1, *args, **kwargs)

    def sample(self):
        sample = Variable(torch.multinomial(self.ps.data, 1, replacement=True))
        if self.one_hot:
            # convert to onehot vector
            return _to_one_hot(sample, self.ps)
        return sample

    # def expanded_sample(self):
        # return Variable(torch.multinomial(self.ps.data, 1, replacement=True))
        # return self.dist.expanded_sample()

    def batch_log_pdf(self, x):
        if x.dim() == 1:
            x = x.unsqueeze(0)
        if self.one_hot:
            if self.ps.size(0) != x.size(0):
                # convert to int torcho one-hot
                _ps = self.ps.expand_as(x)
            else:
                _ps = self.ps
            return torch.sum(x * torch.log(_ps), 1)
        return torch.log(torch.index_select(self.ps, 1, x.squeeze(1).long()))

    def log_pdf(self, _x):
        return torch.sum(self.batch_log_pdf(_x))