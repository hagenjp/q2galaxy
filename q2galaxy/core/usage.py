import os

from qiime2.sdk.usage import DiagnosticUsage

from q2galaxy.core.util import XMLNode
from q2galaxy.core.templaters.helpers import signature_to_galaxy


def collect_test_data(action, test_dir):
    for example in action.examples.values():
        use = TestDataUsage(write_dir=test_dir)
        example(use)
        yield from use._created_files


class TestDataUsage(DiagnosticUsage):
    def __init__(self, write_dir=None):
        super().__init__()
        self.write_dir = write_dir
        self._created_files = []

    def _init_helper(self, ref, factory, ext):
        basename = '.'.join([ref, ext])
        if self.write_dir is not None:
            path = os.path.join(self.write_dir, basename)
            if not os.path.exists(path):
                self._created_files.append(
                    {'status': 'created', 'type': 'file', 'path': path})
            factory().save(path)

        return basename

    def _init_data_(self, ref, factory):
        return self._init_helper(ref, factory, 'qza')

    def _init_metadata_(self, ref, factory):
        return self._init_helper(ref, factory, 'tsv')


class TemplateTestUsage(TestDataUsage):
    def __init__(self):
        super().__init__()
        self.xml = XMLNode('test')
        self._output_lookup = {}

    def _make_params(self, action, input_opts):
        _, sig = action.get_action()

        for case in signature_to_galaxy(sig, input_opts):
            test_xml = case.tests_xml()
            if test_xml is not None:
                self.xml.append(case.tests_xml())

    def _make_outputs(self, output_opts):
        for output_name, output in output_opts.items():
            output_xml = XMLNode('output', name=output_name, ftype='qza')
            self._output_lookup[output] = output_xml
            self.xml.append(output_xml)

    def _action_(self, action, input_opts: dict, output_opts: dict):
        self._make_params(action, input_opts)
        self._make_outputs(output_opts)

        return super()._action_(action, input_opts, output_opts)

    def _assert_has_line_matching_(self, ref, label, path, expression):
        output = self._output_lookup[ref]

        contents = output.find('assert_contents')
        if contents is None:
            contents = XMLNode('assert_contents')
            output.append(contents)

        path = f'.*/data/{path}'
        archive = contents.find(f'has_archive_member[@path="{path}"]')
        if archive is None:
            archive = XMLNode('has_archive_member', path=path)
            contents.append(archive)

        archive.append(XMLNode('has_line_matching', expression=expression))