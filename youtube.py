from apiclient.discovery import build
import math


kind_to_item = {
}


def kind(kind_str):
    def subscribe(cls):
        kind_to_item[kind_str] = cls
        return cls
    return subscribe


def get_item(raw_item):
    cls = kind_to_item[raw_item['id']['kind']]
    return cls(raw_item)


class Thumbnail(object):
    def __init__(self, raw_thumbnail):
        self.raw_thumbnail = raw_thumbnail
        self.url = raw_thumbnail['url']
        self.width = raw_thumbnail['width']
        self.height = raw_thumbnail['height']

    def __repr__(self):
        return '<{} url={!r}>'.format(
            self.__class__.__name__,
            self.url
        )


class Item(object):
    def __init__(self, raw_item):
        self.raw_item = raw_item
        self.title = raw_item['snippet']['title']
        self.default_thumbnail = Thumbnail(
            raw_item['snippet']['thumbnails']['default'])
        self.medium_thumbnail = Thumbnail(
            raw_item['snippet']['thumbnails']['medium'])
        self.high_thumbnail = Thumbnail(
            raw_item['snippet']['thumbnails']['high'])

    def __repr__(self):
        attrs = []
        if self.id:
            attrs.append('id={!r}'.format(self.id))
        attrs.append('title={!r}'.format(self.title))
        return '<{} {}>'.format(
            self.__class__.__name__,
            ', '.join(attrs)
        )


@kind('youtube#video')
class Video(Item):
    def __init__(self, raw_item):
        super(Video, self).__init__(raw_item)
        self.id = raw_item['id']['videoId']

    @property
    def url(self):
        return 'https://www.youtube.com/watch?v={}'.format(self.id)

    def download(self):
        # Put the import here because the import takes time.
        # I don't know why yet.
        import youtube_dl
        with youtube_dl.YoutubeDL() as ydl:
            ydl.download([self.url])


@kind('youtube#channel')
class Channel(Item):
    def __init__(self, raw_item):
        super(Channel, self).__init__(raw_item)
        self.id = raw_item['id']['channelId']


@kind('youtube#playlist')
class Playlist(Item):
    def __init__(self, raw_item):
        super(Playlist, self).__init__(raw_item)
        self.id = raw_item['id']['playlistId']


class Page(object):
    def __init__(self, response, youtube, query, page_no=1):
        self.query = query
        self.page_no = page_no
        self.response = response
        self.items = list(map(get_item, response['items']))
        self.previous_page_token = response.get('prevPageToken')
        self.next_page_token = response.get('nextPageToken')
        self._youtube = youtube

    def has_next_page(self):
        return bool(self.next_page_token)

    def get_next_page(self):
        return self._youtube.get_page_by_token(
            self.next_page_token, self.query, self.page_no + 1)

    def __repr__(self):
        return '<{} #{} for {!r}>'.format(
            self.__class__.__name__,
            self.page_no,
            self.query,
        )


class ResultSet(object):
    def __init__(self, parameters, youtube):
        self.parameters = parameters
        self.pages = []
        self._youtube = youtube
        self.query = parameters['q']

        # Response of the first page.
        self.response = None
        self._nb_results = None
        self._results_per_page = None

    @property
    def nb_results(self):
        if not self._nb_results:
            self._fetch_first_page()
        return self._nb_results

    @property
    def nb_pages(self):
        return int(math.ceil(
            float(self.nb_results) / float(self._results_per_page)))

    def _fetch_first_page(self):
        self.response = self._youtube.query(**self.parameters)
        self._nb_results = self.response['pageInfo']['totalResults']
        self._results_per_page = self.response['pageInfo']['resultsPerPage']
        initial_page = Page(self.response, self._youtube, self.query)
        self.pages.append(initial_page)

    def items(self):
        for page in self:
            for item in page.items:
                yield item

    def __iter__(self):
        # Fetch the first page and append it to `self.pages`
        if not self.pages:
            self._fetch_first_page()

        for page in self.pages:
            yield page

        last_page = self.pages[-1]
        while last_page.has_next_page():
            last_page = last_page.get_next_page()
            self.pages.append(last_page)
            yield last_page

    def __repr__(self):
        return '<{} for {!r}>'.format(
            self.__class__.__name__,
            self.query,
        )


class Youtube(object):
    api_service_name = 'youtube'
    api_version = 'v3'

    def __init__(self, developer_key):
        self._youtube = build(self.api_service_name, self.api_version,
                              developerKey=developer_key)

    def search(self, query, include_video=True, include_channel=False,
               include_playlist=False, max_results=50):
        accepted_types = []

        if include_video:
            accepted_types.append('video')
        if include_channel:
            accepted_types.append('channel')
        if include_playlist:
            accepted_types.append('playlist')

        if not (0 <= max_results <= 50):
            raise ValueError('`max_results` should be between 0 and 50 '
                             '(0 and 50 included)')

        parameters = {
            'q': query,
            'part': 'id,snippet',
            'maxResults': max_results,
            'safeSearch': 'none',
            'type': ','.join(accepted_types),
        }
        return ResultSet(parameters, self)

    def get_page_by_token(self, token, query, page_no):
        response = self.query(pageToken=token)
        return Page(response, self, query, page_no)

    def query(self, **parameters):
        if 'part' not in parameters:
            parameters['part'] = 'id,snippet'
        return self._youtube.search().list(**parameters).execute()
